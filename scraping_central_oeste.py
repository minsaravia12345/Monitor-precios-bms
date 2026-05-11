import time
import os
import re
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse

# --- CONFIGURACIÓN ---
ARCHIVO_KILLERS = r"C:\Users\b_saravia\OneDrive - Farmacity\Documents\skillers\Killers evento.xlsx"
ARCHIVO_FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "killers_urls_fallback.xlsx")

# Cargar URLs de fallback para usarlas como prioridad
urls_prioridad = {}
if os.path.exists(ARCHIVO_FALLBACK):
    try:
        df_fb_cache = pd.read_excel(ARCHIVO_FALLBACK)
        # Filtrar solo para esta farmacia
        df_fb_cache = df_fb_cache[df_fb_cache['Farmacia'].str.lower().str.contains('central', na=False)]
        for _, row in df_fb_cache.iterrows():
            ean_fb = str(row.get('EAN', '')).strip()
            nom_fb = str(row.get('Nombre', '')).strip()
            url_fb = str(row.get('URL', '')).strip()
            if url_fb and url_fb != 'nan':
                # Usamos una llave combinada para ser ultra precisos
                urls_prioridad[f"{ean_fb}_{nom_fb}"] = url_fb
    except: pass

def limpiar_precio(texto):
    if not texto: return 0
    solo_numeros = re.sub(r'\D', '', str(texto))
    if not solo_numeros: return 0
    try:
        # Los precios en Central Oeste suelen tener 2 decimales (ej: $ 1.234,00 -> 123400 -> 1234)
        # Si el texto original NO tiene coma ni punto antes de los ultimos 2 digitos, cuidado, pero BeautifulSoup saca el texto limpio.
        if ',' in str(texto) or '.' in str(texto):
             return int(solo_numeros[:-2])
        return int(solo_numeros)
    except:
        return 0

# --- INICIO REQUESTS ---
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
})

print("--- INICIANDO SCRAPER CENTRAL OESTE (DIRECTO A KILLERS) ---")
print("-> MODO ULTRA RÁPIDO (SIN SELENIUM)")

productos_extraidos = []

# --- FASE 1: BÚSQUEDA DIRIGIDA POR KILLERS ---
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
                nombre_limpio = re.sub(r'^\d+\s*-\s*', '', nombre_k).strip()
                nombre_corto = " ".join(nombre_limpio.split()[:3]) # Primeras 3 palabras
                
                # Nombre seguro: quitamos palabras con caracteres corruptos () 
                palabras_limpias = [p for p in nombre_limpio.split() if '' not in p]
                nombre_seguro = " ".join(palabras_limpias[:3])
                
                killers_a_buscar.append({'ean': ean_k, 'nombre_raw': nombre_k, 'nombre_limpio': nombre_limpio, 'nombre_corto': nombre_corto, 'nombre_seguro': nombre_seguro})
        
        print(f"Se procesarán {len(killers_a_buscar)} Killers.")
        
        for k in killers_a_buscar:
            ean = k['ean']
            nombre_limpio = k['nombre_limpio']
            nombre_corto = k['nombre_corto']
            print(f"  -> Procesando: {k['nombre_raw'][:50]}...")
            
            urls_a_probar = []
            
            # --- NUEVO: PRIORIDAD SI YA EXISTE EN FALLBACK ---
            key_fb = f"{ean}_{k['nombre_raw']}"
            if key_fb in urls_prioridad:
                url_directa = urls_prioridad[key_fb]
                print(f"     [*] Usando URL de prioridad: {url_directa}")
                urls_a_probar.append((url_directa, "URL Prioridad"))
            else:
                # Si no hay prioridad, armamos la lista de búsqueda normal
                if ean: urls_a_probar.append((f"https://www.centraloeste.com.ar/catalogsearch/result/?q={ean}", "EAN"))
                if nombre_limpio: urls_a_probar.append((f"https://www.centraloeste.com.ar/catalogsearch/result/?q={urllib.parse.quote(nombre_limpio)}", "Nombre Completo"))
                if nombre_corto and nombre_corto != nombre_limpio: urls_a_probar.append((f"https://www.centraloeste.com.ar/catalogsearch/result/?q={urllib.parse.quote(nombre_corto)}", "Nombre Corto"))
                if k.get('nombre_seguro') and k.get('nombre_seguro') != k.get('nombre_corto') and k.get('nombre_seguro') != '':
                    urls_a_probar.append((f"https://www.centraloeste.com.ar/catalogsearch/result/?q={urllib.parse.quote(k['nombre_seguro'])}", "Nombre Seguro"))
            
            encontrado = False
            for target_url, tipo_busqueda in urls_a_probar:
                if encontrado: break
                
                try:
                    res = session.get(target_url, timeout=15)
                    if res.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(res.text, 'html.parser')
                    
                    # Verificamos si estamos en una página de producto directo (redirección o URL directa)
                    is_product_page = len(soup.select(".product-info-main")) > 0 and "catalogsearch/result" not in res.url
                    
                    if is_product_page:
                        # Extraer datos de la página del producto directo
                        try:
                            nombre_elem = soup.find(itemprop='name')
                            nombre = nombre_elem.text.strip() if nombre_elem else soup.select_one(".page-title span").text.strip()
                        except:
                            nombre = f"Producto Encontrado ({tipo_busqueda})"
                            
                        precio_final = 0
                        precio_lista = 0
                        porcentaje_oferta = 0
                        stock = "Con Stock"
                        
                        if soup.select_one(".stock.unavailable"):
                            precio_final = "Sin Stock"
                            precio_lista = "Sin Stock"
                            stock = "Sin Stock"
                        else:
                            price_box = soup.select_one(".product-info-main .price-box")
                            if price_box:
                                final_elem = price_box.select_one("[data-price-type='finalPrice'] .price")
                                if final_elem:
                                    precio_final = limpiar_precio(final_elem.text)
                                else:
                                    final_elem = price_box.select_one(".price")
                                    if final_elem: precio_final = limpiar_precio(final_elem.text)
                                
                                old_elem = price_box.select_one("[data-price-type='oldPrice'] .price")
                                if old_elem:
                                    precio_lista = limpiar_precio(old_elem.text)
                                else:
                                    precio_lista = precio_final
                            
                            if isinstance(precio_lista, int) and isinstance(precio_final, int) and precio_lista > 0 and precio_final < precio_lista:
                                porcentaje_oferta = round(((precio_lista - precio_final) / precio_lista) * 100, 2)
                        
                        sku = "N/A"
                        sku_elem = soup.select_one(".product.attribute.sku .value")
                        if sku_elem: sku = sku_elem.text.strip()
                                
                        # VALIDACIÓN ESTRICTA: Si buscamos por nombre, exigimos que el SKU coincida con nuestro EAN
                        if tipo_busqueda != "EAN" and k['ean'] and k['ean'] != 'nan' and sku != "N/A" and sku != k['ean']:
                            print(f"     [!] Descartado ({tipo_busqueda}): SKU de la web ({sku}) != EAN oficial ({k['ean']})")
                            encontrado = False
                            # No rompemos el loop for, dejamos que intente el próximo método de búsqueda
                        else:
                            productos_extraidos.append({
                                'Grupo': 'Killers',
                                'Farmacia': 'Central_Oeste',
                                'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                'EAN': sku if sku != "N/A" else (ean if ean else 'N/A'),
                                'Nombre': nombre,
                                'Precio_Lista': precio_lista,
                                'Precio_Final': precio_final,
                                'Porcentaje_Oferta': porcentaje_oferta,
                                'Stock': stock,
                                'Link': res.url,
                                'EAN_Original': k['ean'],
                                'Nombre_Original': k['nombre_raw']
                            })
                            print(f"     [OK] Encontrado (Producto directo por {tipo_busqueda}): {nombre}")
                            encontrado = True


                    else:
                        # Extraer datos de la lista de resultados
                        items = soup.select("ol.product-items li.product-item")
                        
                        if items:
                            item = items[0]
                            link_elem = item.select_one("a.product-item-link")
                            nombre = link_elem.text.strip() if link_elem else "Producto"
                            link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else target_url
                            
                            precio_final = 0
                            precio_lista = 0
                            porcentaje_oferta = 0
                            stock = "Con Stock"
                            
                            if item.select_one(".stock.unavailable"):
                                precio_final = "Sin Stock"
                                precio_lista = "Sin Stock"
                                stock = "Sin Stock"
                            else:
                                price_box = item.select_one(".price-box")
                                if price_box:
                                    final_elem = price_box.select_one("[data-price-type='finalPrice'] .price")
                                    if final_elem:
                                        precio_final = limpiar_precio(final_elem.text)
                                    else:
                                        final_elem = price_box.select_one(".price")
                                        if final_elem: precio_final = limpiar_precio(final_elem.text)
                                        
                                    old_elem = price_box.select_one("[data-price-type='oldPrice'] .price")
                                    if old_elem:
                                        precio_lista = limpiar_precio(old_elem.text)
                                    else:
                                        precio_lista = precio_final
                                    
                                if isinstance(precio_lista, int) and isinstance(precio_final, int) and precio_lista > 0 and precio_final < precio_lista:
                                    porcentaje_oferta = round(((precio_lista - precio_final) / precio_lista) * 100, 2)
                                
                            sku = "N/A"
                            form_elem = item.select_one("form[data-product-sku]")
                            if form_elem and 'data-product-sku' in form_elem.attrs:
                                sku = form_elem['data-product-sku']
                            
                            # VALIDACIÓN ESTRICTA: Si buscamos por nombre, exigimos que el SKU coincida con nuestro EAN
                            if tipo_busqueda != "EAN" and k['ean'] and k['ean'] != 'nan' and sku != "N/A" and sku != k['ean']:
                                print(f"     [!] Descartado ({tipo_busqueda}): SKU de la web ({sku}) != EAN oficial ({k['ean']})")
                                encontrado = False
                            else:
                                productos_extraidos.append({
                                    'Grupo': 'Killers',
                                    'Farmacia': 'Central_Oeste',
                                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                                    'EAN': sku if sku != "N/A" else (ean if ean else 'N/A'),
                                    'Nombre': nombre,
                                    'Precio_Lista': precio_lista,
                                    'Precio_Final': precio_final,
                                    'Porcentaje_Oferta': porcentaje_oferta,
                                    'Stock': stock,
                                    'Link': link,
                                    'EAN_Original': k['ean'],
                                    'Nombre_Original': k['nombre_raw']
                                })
                                print(f"     [OK] Encontrado ({tipo_busqueda}): {nombre}")
                                encontrado = True
                except Exception as e:
                    print(f"     [!] Error procesando {tipo_busqueda}: {e}")
                    pass
                    
            if not encontrado:
                print(f"     [!] No encontrado o sin stock en ningún intento.")
                
    except Exception as e:
        print(f"Error en Fase 1: {e}")
else:
    print(f"Archivo de Killers no encontrado: {ARCHIVO_KILLERS}")

# --- FASE 2: URLs DE FALLBACK MANUAL ---
print("\n--- FASE 2: PROCESANDO URLs DE FALLBACK MANUAL ---")
eans_ya_encontrados = {re.sub(r'\.0$', '', str(p.get('EAN', ''))).strip() for p in productos_extraidos}

if os.path.exists(ARCHIVO_FALLBACK):
    try:
        df_fb = pd.read_excel(ARCHIVO_FALLBACK)
        if not df_fb.empty and 'Farmacia' in df_fb.columns and 'URL' in df_fb.columns:
            df_fb = df_fb[df_fb['Farmacia'].str.lower().str.contains('central', na=False)]
            print(f"Se encontraron {len(df_fb)} URLs de Fallback para Central Oeste.")
            
            for _, row in df_fb.iterrows():
                ean = str(row.get('EAN', '')).strip()
                if ean in eans_ya_encontrados: continue
                
                url_fb = str(row.get('URL', '')).strip()
                if not url_fb or url_fb == 'nan': continue
                
                print(f"  -> Procesando URL Fallback EAN {ean}: {url_fb}")
                
                try:
                    res = session.get(url_fb, timeout=15)
                    if res.status_code != 200:
                        print("     [!] URL retornó error HTTP", res.status_code)
                        continue
                        
                    soup = BeautifulSoup(res.text, 'html.parser')
                    
                    try:
                        nombre_elem = soup.find(itemprop='name')
                        nombre = nombre_elem.text.strip() if nombre_elem else soup.select_one(".page-title span").text.strip()
                    except:
                        nombre = f"Producto Fallback {ean}"
                            
                    precio_final = 0
                    precio_lista = 0
                    porcentaje_oferta = 0
                    stock = "Con Stock"
                    
                    if soup.select_one(".stock.unavailable"):
                        precio_final = "Sin Stock"
                        precio_lista = "Sin Stock"
                        stock = "Sin Stock"
                    else:
                        price_box = soup.select_one(".product-info-main .price-box")
                        if price_box:
                            final_elem = price_box.select_one("[data-price-type='finalPrice'] .price")
                            if final_elem:
                                precio_final = limpiar_precio(final_elem.text)
                            else:
                                final_elem = price_box.select_one(".price")
                                if final_elem: precio_final = limpiar_precio(final_elem.text)
                            
                            old_elem = price_box.select_one("[data-price-type='oldPrice'] .price")
                            if old_elem:
                                precio_lista = limpiar_precio(old_elem.text)
                            else:
                                precio_lista = precio_final
                        
                        if isinstance(precio_lista, int) and isinstance(precio_final, int) and precio_lista > 0 and precio_final < precio_lista:
                            porcentaje_oferta = round(((precio_lista - precio_final) / precio_lista) * 100, 2)
                        
                    productos_extraidos.append({
                        'Grupo': 'Killers',
                        'Farmacia': 'Central_Oeste',
                        'Fecha': datetime.now().strftime("%Y-%m-%d"),
                        'EAN': ean,
                        'Nombre': nombre,
                        'Precio_Lista': precio_lista,
                        'Precio_Final': precio_final,
                        'Porcentaje_Oferta': porcentaje_oferta,
                        'Stock': stock,
                        'Link': url_fb,
                        'EAN_Original': ean,
                        'Nombre_Original': str(row.get('Nombre', f"Producto Fallback {ean}"))
                    })
                    print(f"     [OK] Encontrado vía Fallback: {nombre}")
                except Exception as e:
                    print(f"     [!] Error procesando URL Fallback: {e}")
    except Exception as e:
        print(f"Error en Fase 2: {e}")

# --- GUARDAR ---
if productos_extraidos:
    df_out = pd.DataFrame(productos_extraidos)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resultados_scraping", f"Output_CentralOeste_Magento_{ts}.xlsx")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df_out = df_out.drop_duplicates(subset=['EAN', 'Nombre'])
    df_out.to_excel(path, index=False)
    print(f"\n¡Éxito! Guardados {len(df_out)} productos en: {path}")
else:
    print("\nNo se extrajeron datos.")