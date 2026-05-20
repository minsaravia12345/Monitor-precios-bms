import time
import requests
from datetime import datetime
import pandas as pd
import os
import re

ARCHIVO_KILLERS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Killers evento.xlsx")
ARCHIVO_FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "killers_urls_fallback.xlsx")

# Cargar URLs de fallback para usarlas como prioridad
urls_prioridad = {}
if os.path.exists(ARCHIVO_FALLBACK):
    try:
        df_fb_cache = pd.read_excel(ARCHIVO_FALLBACK)
        # Filtrar solo para esta farmacia
        df_fb_cache = df_fb_cache[df_fb_cache['Farmacia'].str.lower().str.contains('farmacity', na=False)]
        for _, row in df_fb_cache.iterrows():
            ean_fb = str(row.get('EAN', '')).strip()
            nom_fb = str(row.get('Nombre', '')).strip()
            url_fb = str(row.get('URL', '')).strip()
            if url_fb and url_fb != 'nan':
                # Usamos una llave combinada para ser ultra precisos
                urls_prioridad[f"{ean_fb}_{nom_fb}"] = url_fb
    except: pass

print("--- INICIANDO SCRAPER FARMACITY (DIRECTO A KILLERS) ---")

productos_extraidos = []

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
})

# --- FASE 1: BÚSQUEDA DIRIGIDA POR KILLERS (EAN, SKU ID & NOMBRE) ---
print("\n--- FASE 1: BÚSQUEDA DE KILLERS ---")
if os.path.exists(ARCHIVO_KILLERS):
    try:
        df_killers = pd.read_excel(ARCHIVO_KILLERS, dtype={'EAN': str})
        col_nombre = [c for c in df_killers.columns if 'Descripci' in c]
        col_nombre = col_nombre[0] if col_nombre else 'Nombre'
        
        killers_a_buscar = []
        for _, row in df_killers.iterrows():
            ean_k = str(row.get('EAN', '')).strip()
            if ean_k.lower() == 'nan': ean_k = ''
            if 'e' in ean_k.lower() or '.' in ean_k:
                try: ean_k = format(float(ean_k), '.0f')
                except: pass
            ean_k = re.sub(r'\.0$', '', ean_k).strip()
            
            nombre_k = str(row.get(col_nombre, row.get('Nombre', ''))).strip()
            if nombre_k.lower() == 'nan': nombre_k = ''
            
            if ean_k or (not ean_k and nombre_k):
                sku_match = re.search(r'^(\d{5,8})', nombre_k)
                sku_id = sku_match.group(1) if sku_match else None
                nombre_limpio = re.sub(r'^\d+\s*-\s*', '', nombre_k).strip()
                nombre_corto = " ".join(nombre_limpio.split()[:3]) # Primeras 3 palabras
                
                # Nombre seguro: quitamos palabras con caracteres corruptos () 
                palabras_limpias = [p for p in nombre_limpio.split() if '' not in p]
                nombre_seguro = " ".join(palabras_limpias[:3])
                
                killers_a_buscar.append({'ean': ean_k, 'sku': sku_id, 'nombre_raw': nombre_k, 'nombre_limpio': nombre_limpio, 'nombre_corto': nombre_corto, 'nombre_seguro': nombre_seguro})

        print(f"Se procesarán {len(killers_a_buscar)} productos.")
        
        import urllib.parse
        for k in killers_a_buscar:
            ean_target = k['ean']
            sku_target = k['sku']
            nombre_limpio = k['nombre_limpio']
            encontrado = False
            res_item = None
            
            print(f"  -> Procesando: {k['nombre_raw'][:50]}...")
            
            # --- NUEVO: PRIORIDAD SI YA EXISTE EN FALLBACK ---
            key_fb = f"{ean_target}_{k['nombre_raw']}"
            if key_fb in urls_prioridad:
                url_directa = urls_prioridad[key_fb]
                print(f"     [*] Usando URL de prioridad: {url_directa}")
                if "/p" in url_directa:
                    slug = url_directa.split("/")[-2] if url_directa.endswith("/p") else url_directa.split("/p")[0].split("/")[-1]
                    api_url = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{slug}/p"
                else:
                    slug = url_directa.strip("/").split("/")[-1]
                    api_url = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{slug}/p"
                
                try:
                    res = session.get(api_url, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado vía URL directa.")
                except: pass

            # --- BÚSQUEDA NORMAL (Solo si no se encontró por URL directa) ---
            if not encontrado and ean_target:
                url_ean = f"https://www.farmacity.com/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{ean_target}"
                try:
                    res = session.get(url_ean, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por EAN: {res_item.get('productName')}")
                except: pass

            if not encontrado and sku_target:
                url_sku = f"https://www.farmacity.com/api/catalog_system/pub/products/search?fq=skuId:{sku_target}"
                try:
                    res = session.get(url_sku, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por SKU ID: {res_item.get('productName')}")
                except: pass
                
            if not encontrado and nombre_limpio:
                url_nombre = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{urllib.parse.quote(nombre_limpio)}"
                try:
                    res = session.get(url_nombre, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por Nombre: {res_item.get('productName')}")
                except: pass

            if not encontrado and k.get('nombre_corto'):
                url_corto = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{urllib.parse.quote(k['nombre_corto'])}"
                try:
                    res = session.get(url_corto, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por Nombre Corto: {res_item.get('productName')}")
                except: pass
                
            if not encontrado and k.get('nombre_seguro') and k.get('nombre_seguro') != k.get('nombre_corto') and k.get('nombre_seguro') != '':
                url_seguro = f"https://www.farmacity.com/api/catalog_system/pub/products/search/{urllib.parse.quote(k['nombre_seguro'])}"
                try:
                    res = session.get(url_seguro, timeout=10)
                    if res.status_code in [200, 206] and res.json():
                        res_item = res.json()[0]
                        encontrado = True
                        print(f"     [OK] Encontrado por Nombre Seguro: {res_item.get('productName')}")
                except: pass

            if encontrado and res_item:
                nombre = res_item.get('productName', '')
                link = res_item.get('link', '')
                try:
                    # Búsqueda inteligente del SKU correcto
                    target_sku = None
                    ean_api = ''
                    if ean_target and ean_target != 'nan':
                        for item in res_item['items']:
                            if str(item.get('ean', '')).strip() == ean_target:
                                target_sku = item
                                ean_api = ean_target
                                break
                                
                        if not target_sku:
                            print(f"     [!] Descartado: EAN esperado {ean_target} no está en las variantes de {nombre}.")
                            encontrado = False
                    else:
                        target_sku = res_item['items'][0]
                        ean_api = str(target_sku.get('ean', '')).strip()
                    
                    if encontrado and target_sku:
                        if 'sellers' in target_sku and len(target_sku['sellers']) > 0 and 'commertialOffer' in target_sku['sellers'][0]:
                            offer = target_sku['sellers'][0]['commertialOffer']
                            qty = int(offer.get('AvailableQuantity', 0))
                            
                            if qty == 0:
                                p_final = "Sin Stock"
                                p_lista = "Sin Stock"
                                porcentaje_oferta = 0
                                stock = "Sin Stock"
                            else:
                                p_final = int(float(offer.get('Price', 0)))
                                p_lista = int(float(offer.get('ListPrice', 0)))
                                porcentaje_oferta = round(((p_lista - p_final) / p_lista * 100), 2) if p_lista > p_final else 0
                                stock = "Con Stock"
                            
                            productos_extraidos.append({
                                'Grupo': 'Killers',
                                'Farmacia': 'Farmacity',
                                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                'EAN': ean_api if (ean_api and ean_api != 'nan') else 'N/A',
                                'Nombre': nombre,
                            'Precio_Lista': p_lista,
                            'Precio_Final': p_final,
                            'Porcentaje_Oferta': porcentaje_oferta,
                            'Stock': stock,
                            'Link': link,
                            'EAN_Original': ean_target,
                            'Nombre_Original': k['nombre_raw']
                        })
                    else:
                        print(f"     [!] Estructura JSON incompleta para {nombre}")
                except Exception as e:
                    print(f"     [!] Error parseando JSON para {nombre}: {e}")
            else:
                print(f"     [!] No disponible en API Farmacity.")
            time.sleep(0.3)
            
    except Exception as e:
        print(f"Error en Fase 1: {e}")
else:
    print(f"Archivo de Killers no encontrado: {ARCHIVO_KILLERS}")

# --- FASE 2: URLs DE FALLBACK MANUAL ---
print("\n--- FASE 2: PROCESANDO URLs DE FALLBACK MANUAL ---")
eans_ya_encontrados = {re.sub(r'\.0$', '', str(p['EAN'])).strip() for p in productos_extraidos}

if os.path.exists(ARCHIVO_FALLBACK):
    try:
        df_fb = pd.read_excel(ARCHIVO_FALLBACK)
        if not df_fb.empty and 'Farmacia' in df_fb.columns and 'URL' in df_fb.columns:
            df_fb = df_fb[df_fb['Farmacia'].str.lower().str.contains('farmacity', na=False)]
            print(f"Se encontraron {len(df_fb)} URLs de Fallback para Farmacity.")
            
            for _, row in df_fb.iterrows():
                ean = str(row.get('EAN', '')).strip()
                if ean in eans_ya_encontrados: continue
                
                url_fb = str(row.get('URL', '')).strip()
                if not url_fb or url_fb == 'nan': continue
                
                print(f"  -> Procesando Fallback EAN {ean}: {url_fb}")
                
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
                                stock = "Sin Stock"
                            else:
                                p_final = int(float(offer.get('Price', 0)))
                                p_lista = int(float(offer.get('ListPrice', 0)))
                                porcentaje_oferta = round(((p_lista - p_final) / p_lista * 100), 2) if p_lista > p_final else 0
                                stock = "Con Stock"
                            
                            productos_extraidos.append({
                                'Grupo': 'Killers',
                                'Farmacia': 'Farmacity',
                                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                'EAN': ean_api if ean_api != 'N/A' else ean,
                                'Nombre': nombre,
                                'Precio_Lista': p_lista,
                                'Precio_Final': p_final,
                                'Porcentaje_Oferta': porcentaje_oferta,
                                'Stock': stock,
                                'Link': link,
                                'EAN_Original': ean,
                                'Nombre_Original': str(row.get('Nombre', f"Producto Fallback {ean}"))
                            })
                            print(f"     [OK] Encontrado vía Fallback: {nombre}")
                        except: pass
                    else:
                        print(f"     [!] No se pudo obtener datos del fallback")
                except Exception as e:
                    pass
    except Exception as e:
        print(f"Error en Fase 2: {e}")

# --- GUARDAR ---
if productos_extraidos:
    df_out = pd.DataFrame(productos_extraidos)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resultados_scraping", f"Output_Farmacity_VTEX_{ts}.xlsx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_out = df_out.drop_duplicates(subset=['EAN', 'Nombre'])
    df_out.to_excel(path, index=False)
    print(f"\n¡Éxito! Guardados {len(df_out)} productos en: {path}")
else:
    print("\nNo se extrajeron datos.")
