import time
import requests
from datetime import datetime
import pandas as pd
import os
import re

# --- CONFIGURACIÓN ---
ARCHIVO_INPUT = r"C:\Users\b_saravia\Downloads\Listado URL - colecciones Farmacity.xlsx" 
# NUEVO: Ruta al Excel de Killers para búsqueda dirigida
ARCHIVO_KILLERS = r"C:\Users\b_saravia\OneDrive - Farmacity\Documents\Precios MercadoLibre.xlsx"

print("--- INICIANDO SCRAPER FARMACITY (VIA API VTEX OPTIMIZADA) ---")

productos_extraidos = []

try:
    df_input = pd.read_excel(ARCHIVO_INPUT)
    lista_input = df_input.to_dict('records')
except Exception as e:
    print(f"Error leyendo Excel de colecciones ({e}).")
    exit()

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
})

# --- FASE 1: SCRAPING GENERAL POR CATEGORÍAS ---
for i, fila in enumerate(lista_input):
    url_base = fila['URL'].strip()
    grupo = fila.get('GRUPO', 'General')
    
    print(f"\n[{i+1}/{len(lista_input)}] Procesando Categoría: {grupo} ({url_base})")
    api_endpoint = url_base.replace("https://www.farmacity.com/", "https://www.farmacity.com/api/catalog_system/pub/products/search/")
    
    for pag in range(10): # Paginamos hasta 500 productos
        _from = pag * 50
        _to = _from + 49
        url_target = f"{api_endpoint}{'&' if '?' in api_endpoint else '?'}_from={_from}&_to={_to}"
        
        print(f"  -> Buscando items {_from} al {_to}...")
        try:
            res = session.get(url_target, timeout=15)
            if res.status_code not in [200, 206]: break
            data = res.json()
            if not data: break
                
            for item in data:
                nombre = item.get('productName', '')
                link = item.get('link', '')
                try: ean = str(item['items'][0].get('ean', 'N/A')).strip()
                except: ean = 'N/A'
                
                try:
                    offer = item['items'][0]['sellers'][0]['commertialOffer']
                    p_final = int(float(offer.get('Price', 0)))
                    p_lista = int(float(offer.get('ListPrice', 0)))
                except: p_final, p_lista = 0, 0
                    
                productos_extraidos.append({
                    'Grupo': grupo,
                    'Farmacia': 'Farmacity',
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'EAN': ean,
                    'Nombre': nombre,
                    'Precio_Lista': p_lista,
                    'Precio_Final': p_final,
                    'Porcentaje_Oferta': round(((p_lista - p_final) / p_lista * 100), 2) if p_lista > p_final else 0,
                    'Link': link
                })
            time.sleep(0.3)
        except: break

# --- FASE 2: BÚSQUEDA DIRIGIDA POR KILLERS (EAN & SKU ID) ---
print("\n--- FASE 2: ASEGURANDO COBERTURA DE KILLERS ---")
if os.path.exists(ARCHIVO_KILLERS):
    try:
        df_killers = pd.read_excel(ARCHIVO_KILLERS)
        eans_ya_encontrados = {re.sub(r'\.0$', '', str(p['EAN'])).strip() for p in productos_extraidos}
        
        # Procesar los killers del excel
        killers_a_buscar = []
        for _, row in df_killers.iterrows():
            ean_k = str(row.get('EAN', ''))
            if 'e' in ean_k.lower() or '.' in ean_k:
                try: ean_k = format(float(ean_k), '.0f')
                except: pass
            ean_k = re.sub(r'\.0$', '', ean_k).strip()
            
            if ean_k and ean_k not in eans_ya_encontrados:
                # Extraer posible SKU ID del nombre (ej: "233160 - ...")
                sku_match = re.search(r'^(\d{5,8})', str(row.get('Nombre', '')))
                sku_id = sku_match.group(1) if sku_match else None
                killers_a_buscar.append({'ean': ean_k, 'sku': sku_id, 'nombre': row.get('Nombre', '')})

        print(f"Se identificaron {len(killers_a_buscar)} Killers faltantes.")
        
        for k in killers_a_buscar:
            ean_target = k['ean']
            sku_target = k['sku']
            encontrado = False
            
            # Intento A: Búsqueda por EAN (Verificada)
            print(f"  -> Buscando EAN: {ean_target}...")
            # NUEVO: Búsqueda exacta por EAN en VTEX usando fq=alternateIds_Ean
            url_ean = f"https://www.farmacity.com/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{ean_target}"
            try:
                res = session.get(url_ean, timeout=10)
                if res.status_code in [200, 206] and res.json():
                    # Como la búsqueda es exacta, el primer resultado debería ser el correcto
                    res_item = res.json()[0]
                    encontrado = True
                    print(f"     [OK] Encontrado por EAN exacto: {res_item.get('productName')}")
            except: pass

            # Intento B: Búsqueda por SKU ID (si falló el EAN)
            if not encontrado and sku_target:
                print(f"     [!] EAN no hallado. Buscando por SKU ID: {sku_target}...")
                url_sku = f"https://www.farmacity.com/api/catalog_system/pub/products/search?fq=skuId:{sku_target}"
                try:
                    res = session.get(url_sku, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por SKU ID: {res_item.get('productName')}")
                except: pass

            if encontrado:
                nombre = res_item.get('productName', '')
                link = res_item.get('link', '')
                # Tomar los datos del primer SKU habilitado
                try:
                    target_sku = res_item['items'][0]
                    ean_api = str(target_sku.get('ean', ean_target)).strip()
                    offer = target_sku['sellers'][0]['commertialOffer']
                    
                    qty = int(offer.get('AvailableQuantity', 0))
                    if qty == 0:
                        p_final = "Sin Stock"
                        p_lista = "Sin Stock"
                        porcentaje_oferta = 0
                    else:
                        p_final = int(float(offer.get('Price', 0)))
                        p_lista = int(float(offer.get('ListPrice', 0)))
                        porcentaje_oferta = round(((p_lista - p_final) / p_lista * 100), 2) if p_lista > p_final else 0
                    
                    productos_extraidos.append({
                        'Grupo': 'Killers-Targeted',
                        'Farmacia': 'Farmacity',
                        'Fecha': datetime.now().strftime("%Y-%m-%d"),
                        'EAN': ean_api,
                        'Nombre': nombre,
                        'Precio_Lista': p_lista,
                        'Precio_Final': p_final,
                        'Porcentaje_Oferta': porcentaje_oferta,
                        'Link': link
                    })
                except: pass
            else:
                print(f"     [!] Agotado o no disponible en Farmacity.")
            time.sleep(0.4)
            
    except Exception as e:
        print(f"Error en Fase 2: {e}")
else:
    print("Archivo de Killers no encontrado. Saltando Fase 2.")

# --- FASE 3: URLs DE FALLBACK MANUAL ---
print("\n--- FASE 3: PROCESANDO URLs DE FALLBACK MANUAL ---")
ARCHIVO_FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "killers_urls_fallback.xlsx")
if os.path.exists(ARCHIVO_FALLBACK):
    try:
        df_fb = pd.read_excel(ARCHIVO_FALLBACK)
        if not df_fb.empty and 'Farmacia' in df_fb.columns and 'URL' in df_fb.columns:
            df_fb = df_fb[df_fb['Farmacia'].str.lower().str.contains('farmacity', na=False)]
            print(f"Se encontraron {len(df_fb)} URLs de Fallback para Farmacity.")
            
            for _, row in df_fb.iterrows():
                ean = str(row.get('EAN', '')).strip()
                url_fb = str(row.get('URL', '')).strip()
                if not url_fb or url_fb == 'nan': continue
                
                print(f"  -> Procesando URL Fallback para EAN {ean}: {url_fb}")
                
                if "/p" in url_fb:
                    slug = url_fb.split("/")[-2] if url_fb.endswith("/p") else url_fb.split("/p")[0].split("/")[-1]
                    api_url = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{slug}/p"
                else:
                    slug = url_fb.strip("/").split("/")[-1]
                    api_url = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{slug}/p"
                    
                try:
                    res = session.get(api_url, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        nombre = res_item.get('productName', '')
                        link = res_item.get('link', url_fb)
                        
                        try:
                            target_sku = res_item['items'][0]
                            ean_api = str(target_sku.get('ean', ean)).strip()
                            offer = target_sku['sellers'][0]['commertialOffer']
                            
                            qty = int(offer.get('AvailableQuantity', 0))
                            if qty == 0:
                                p_final = "Sin Stock"
                                p_lista = "Sin Stock"
                                porcentaje_oferta = 0
                            else:
                                p_final = int(float(offer.get('Price', 0)))
                                p_lista = int(float(offer.get('ListPrice', 0)))
                                porcentaje_oferta = round(((p_lista - p_final) / p_lista * 100), 2) if p_lista > p_final else 0
                            
                            productos_extraidos.append({
                                'Grupo': 'Killers-Fallback',
                                'Farmacia': 'Farmacity',
                                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                'EAN': ean_api if ean_api != 'N/A' else ean,
                                'Nombre': nombre,
                                'Precio_Lista': p_lista,
                                'Precio_Final': p_final,
                                'Porcentaje_Oferta': porcentaje_oferta,
                                'Link': link
                            })
                            print(f"     [OK] Encontrado vía Fallback: {nombre}")
                        except: pass
                    else:
                        print(f"     [!] No se pudo obtener datos de la API para el slug: {slug}")
                except Exception as e:
                    print(f"     [!] Error consultando API de Fallback: {e}")
        else:
            print("Archivo de Fallback vacío o sin columnas requeridas.")
    except Exception as e:
        print(f"Error en Fase 3: {e}")
else:
    print("Archivo de Fallback no encontrado. Saltando Fase 3.")

# --- GUARDAR ---
if productos_extraidos:
    df_out = pd.DataFrame(productos_extraidos)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resultados_scraping", f"Output_Farmacity_VTEX_{ts}.xlsx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_out = df_out.drop_duplicates(subset=['EAN', 'Nombre'])
    df_out.to_excel(path, index=False)
    print(f"\n¡Éxito! Archivo Farmacity finalizado con {len(df_out)} productos en: {path}")
else:
    print("\nNo se extrajeron datos.")

