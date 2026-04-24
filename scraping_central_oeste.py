import time
import json
import os
import re
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. CONFIGURACIÓN ---
ARCHIVO_INPUT = r"C:\Users\b_saravia\Downloads\Listado URL - colecciones Central oeste.xlsx" 
ARCHIVO_KILLERS = r"C:\Users\b_saravia\OneDrive - Farmacity\Documents\Precios MercadoLibre.xlsx"

def limpiar_precio(texto):
    if not texto: return 0
    # En Magento viene tipo "$ 15.000,00" -> Dejamos solo números
    solo_numeros = re.sub(r'\D', '', texto)
    if not solo_numeros: return 0
    # Eliminamos los últimos 2 dígitos (centavos)
    try:
        return int(solo_numeros[:-2])
    except:
        return 0

# --- 2. INICIO DRIVER ---
chrome_options = Options()
chrome_options.add_argument("--headless") # Agregado para ejecución en servidor/agente
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--start-maximized")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

print("--- INICIANDO SCRAPER (MODO MAGENTO) ---")

try:
    df_input = pd.read_excel(ARCHIVO_INPUT)
    if 'URL' not in df_input.columns:
        print("Error: Falta columna 'URL' en el Excel.")
        driver.quit()
        exit()
    lista_input = df_input.to_dict('records')
except Exception as e:
    print(f"Error leyendo Excel: {e}")
    driver.quit()
    exit()

productos_extraidos = []

for i, fila in enumerate(lista_input):
    url_base = fila['URL']
    grupo = fila.get('GRUPO', 'General')
    
    print(f"\n[{i+1}/{len(lista_input)}] Procesando: {grupo}")
    
    if "?p=" in url_base: url_base = url_base.split("?p=")[0]
    
    paginas_a_revisar = 10
    
    for pag in range(1, paginas_a_revisar + 1):
        target_url = f"{url_base}?p={pag}"
        print(f" -> Navegando Pág {pag}: {target_url}")
        
        driver.get(target_url)
        
        try:
            xpath_items = "//ol[contains(@class, 'product-items')]//li[contains(@class, 'product-item')]"
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_items)))
        except TimeoutException:
            print("    [!] No se encontraron productos o fin de paginación.")
            break
            
        items = driver.find_elements(By.XPATH, xpath_items)
        if not items: break
        
        print(f"    Encontrados: {len(items)} productos.")
        
        for item in items:
            try:
                # 1. Nombre y Link
                elem_link = item.find_element(By.XPATH, ".//a[contains(@class, 'product-item-link')]")
                nombre = elem_link.text.strip()
                link = elem_link.get_attribute("href")
                
                # 2. Precios
                precio_final = 0
                precio_lista = 0
                
                try:
                    price_box = item.find_element(By.XPATH, ".//div[contains(@class, 'price-box')]")
                    
                    # Intento Precio Final
                    try:
                        txt_final = price_box.find_element(By.XPATH, ".//span[@data-price-type='finalPrice']//span[@class='price']").text
                        precio_final = limpiar_precio(txt_final)
                    except:
                        try:
                            txt_final = price_box.find_element(By.CSS_SELECTOR, ".price").text
                            precio_final = limpiar_precio(txt_final)
                        except:
                            precio_final = 0

                    # Intento Precio Lista (Tachado)
                    try:
                        txt_old = price_box.find_element(By.XPATH, ".//span[@data-price-type='oldPrice']//span[@class='price']").text
                        precio_lista = limpiar_precio(txt_old)
                    except:
                        precio_lista = precio_final 
                except:
                    precio_final = 0
                    precio_lista = 0

                # --- 3. CÁLCULO DE PORCENTAJE DE OFERTA ---
                porcentaje_oferta = 0
                if precio_lista > 0 and precio_final < precio_lista:
                    # Calculamos el % de descuento (ej: 25.0)
                    porcentaje_oferta = round(((precio_lista - precio_final) / precio_lista) * 100, 2)

                # 4. SKU
                sku = "N/A"
                try:
                    form = item.find_element(By.XPATH, ".//form[@data-product-sku]")
                    sku = form.get_attribute("data-product-sku")
                except:
                    pass

                productos_extraidos.append({
                    'Grupo': grupo,
                    'Fecha': datetime.now().strftime("%Y-%m-%d"),
                    'EAN': sku,
                    'Nombre': nombre,
                    'Precio_Lista': precio_lista,
                    'Precio_Final': precio_final,
                    'Porcentaje_Oferta': porcentaje_oferta,
                    'Link': link
                })
                
            except Exception:
                continue

# --- FASE 2: BÚSQUEDA DIRIGIDA POR KILLERS ---
print("\n--- FASE 2: ASEGURANDO COBERTURA DE KILLERS ---")
if os.path.exists(ARCHIVO_KILLERS):
    try:
        df_killers = pd.read_excel(ARCHIVO_KILLERS)
        eans_ya_encontrados = {re.sub(r'\.0$', '', str(p.get('EAN', ''))).strip() for p in productos_extraidos}
        
        killers_a_buscar = []
        for x in df_killers['EAN'].dropna():
            s = str(x)
            if 'e' in s.lower() or '.' in s:
                try: s = format(float(s), '.0f')
                except: pass
            s = re.sub(r'\.0$', '', s).strip()
            if s and s not in eans_ya_encontrados:
                killers_a_buscar.append(s)
        
        print(f"Se identificaron {len(killers_a_buscar)} Killers faltantes.")
        
        for ean in killers_a_buscar:
            print(f"  -> Buscando EAN Killer: {ean}...")
            target_url = f"https://www.centraloeste.com.ar/catalogsearch/result/?q={ean}"
            driver.get(target_url)
            
            try:
                # Esperar a ver si hay productos
                xpath_items = "//ol[contains(@class, 'product-items')]//li[contains(@class, 'product-item')]"
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath_items)))
                items = driver.find_elements(By.XPATH, xpath_items)
                
                if items:
                    item = items[0]
                    elem_link = item.find_element(By.XPATH, ".//a[contains(@class, 'product-item-link')]")
                    nombre = elem_link.text.strip()
                    link = elem_link.get_attribute("href")
                    
                    precio_final = 0
                    precio_lista = 0
                    try:
                        price_box = item.find_element(By.XPATH, ".//div[contains(@class, 'price-box')]")
                        try:
                            txt_final = price_box.find_element(By.XPATH, ".//span[@data-price-type='finalPrice']//span[@class='price']").text
                            precio_final = limpiar_precio(txt_final)
                        except:
                            try:
                                txt_final = price_box.find_element(By.CSS_SELECTOR, ".price").text
                                precio_final = limpiar_precio(txt_final)
                            except: pass
                            
                        try:
                            txt_old = price_box.find_element(By.XPATH, ".//span[@data-price-type='oldPrice']//span[@class='price']").text
                            precio_lista = limpiar_precio(txt_old)
                        except:
                            precio_lista = precio_final
                    except: pass
                    
                    porcentaje_oferta = 0
                    if precio_lista > 0 and precio_final < precio_lista:
                        porcentaje_oferta = round(((precio_lista - precio_final) / precio_lista) * 100, 2)
                        
                    sku = "N/A"
                    try:
                        form = item.find_element(By.XPATH, ".//form[@data-product-sku]")
                        sku = form.get_attribute("data-product-sku")
                    except: pass
                    
                    productos_extraidos.append({
                        'Grupo': 'Killers-Targeted',
                        'Fecha': datetime.now().strftime("%Y-%m-%d"),
                        'EAN': sku if sku != "N/A" else ean,
                        'Nombre': nombre,
                        'Precio_Lista': precio_lista,
                        'Precio_Final': precio_final,
                        'Porcentaje_Oferta': porcentaje_oferta,
                        'Link': link
                    })
                    print(f"     [OK] Encontrado: {nombre}")
                else:
                    print(f"     [!] No encontrado.")
            except TimeoutException:
                print(f"     [!] No encontrado o sin stock.")
            except Exception as e:
                print(f"     [!] Error procesando EAN: {e}")
                
    except Exception as e:
        print(f"Error en Fase 2: {e}")
else:
    print("Archivo de Killers no encontrado. Saltando Fase 2.")

driver.quit()

# --- 5. GUARDAR ---
if productos_extraidos:
    df_out = pd.DataFrame(productos_extraidos)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Resultados_scraping", f"Output_CentralOeste_Magento_{ts}.xlsx")

    # Intentar crear carpeta si no existe
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    df_out.to_excel(path, index=False)
    print(f"\n¡Éxito! Archivo guardado: {path}")
else:
    print("\nNo se extrajo nada. Verifica los selectores o la conexión.")