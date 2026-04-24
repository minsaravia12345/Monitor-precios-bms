import os
import pandas as pd
import json
from glob import glob
from datetime import datetime

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_RESULTADOS = os.path.join(BASE_DIR, "Resultados_scraping")
OUTPUT_JSON = os.path.join(BASE_DIR, "dashboard", "public", "datos_consolidados.json")
# Ruta al Excel manual de MercadoLibre
RUTA_ML = r"C:\Users\b_saravia\OneDrive - Farmacity\Documents\Precios MercadoLibre.xlsx"

# Lista de farmacias soportadas (nombre interno, patron de archivo)
FARMACIAS = [
    ("Central_Oeste", "CentralOeste"),
    ("Farmacity",     "Farmacity"),
    ("Farmaonline",   "Farmaonline"),
]

print("--- INICIANDO CONSOLIDACIÓN ---")

archivos = glob(os.path.join(CARPETA_RESULTADOS, "*.xlsx"))
# Excluir archivos de comparación previos
archivos = [f for f in archivos if "Comparacion_" not in os.path.basename(f)]

dfs = {}
for nombre_farmacia, patron in FARMACIAS:
    encontrados = sorted([f for f in archivos if patron in f], reverse=True)
    if encontrados:
        df = pd.read_excel(encontrados[0])
        df['Farmacia'] = nombre_farmacia
        dfs[nombre_farmacia] = df
        print(f"Cargado {nombre_farmacia}: {os.path.basename(encontrados[0])} ({len(df)} productos)")

# --- CARGAR MERCADOLIBRE (MANUAL) ---
df_ml = pd.DataFrame()
if os.path.exists(RUTA_ML):
    try:
        df_ml = pd.read_excel(RUTA_ML)
        df_ml['Farmacia'] = 'MercadoLibre'
        # Asegurar que EAN sea string y no tenga .0 si vino de float
        df_ml['EAN'] = df_ml['EAN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        print(f"Cargado MercadoLibre (Manual): {len(df_ml)} productos Killers")
    except Exception as e:
        print(f"Error leyendo MercadoLibre (Asegúrate que el archivo no esté abierto): {e}")
else:
    print(f"No se encontró el archivo de MercadoLibre en {RUTA_ML}")

if not dfs and df_ml.empty:
    print("No se encontraron archivos de scraping ni de MercadoLibre. Abortando.")
    exit()

# Concatenar todo para procesar
fuentes = list(dfs.values())
if not df_ml.empty:
    fuentes.append(df_ml)

df_total = pd.concat(fuentes, ignore_index=True)

# --- Agrupar productos por EAN ---
productos_dict = {}

# Identificar EANs de Killers para marcarlos después
eans_killers = set(df_ml['EAN'].tolist()) if not df_ml.empty else set()

import re

for _, row in df_total.iterrows():
    ean_raw = str(row.get('EAN', row['Nombre']))
    # Manejar notación científica si viene de Excel como float
    if 'e' in ean_raw.lower() or '.' in ean_raw:
        try:
            ean_raw = format(float(ean_raw), '.0f')
        except:
            pass
    ean_val = re.sub(r'\.0$', '', ean_raw).strip().lower()
    clave = ean_val
    if clave == "n/a" or not clave:
        clave = str(row['Nombre']).lower().strip()

    if clave not in productos_dict:
        productos_dict[clave] = {
            "Id": clave,
            "EAN": re.sub(r'\.0$', '', str(row.get('EAN', 'N/A'))),
            "Nombre": row['Nombre'],
            "Grupo": row.get('Grupo', 'Variados'),
            "Es_Killer": re.sub(r'\.0$', '', str(row.get('EAN', ''))) in eans_killers,
            "Precios": {}
        }

    farmacia = row['Farmacia']
    productos_dict[clave]["Precios"][farmacia] = {
        "Precio_Final": row['Precio_Final'],
        "Precio_Lista": row['Precio_Lista'],
        "Descuento": row.get('Porcentaje_Oferta', 0),
        "Link": row.get('Link', '#')
    }

# --- Determinar ganador entre TODAS las farmacias (Incluyendo ML) ---
lista_final = []
nombres_farmacias = [f[0] for f in FARMACIAS] + ["MercadoLibre"]

for k, v in productos_dict.items():
    precios = v["Precios"]

    # Obtener precio final de cada farmacia (inf si no existe)
    precios_validos = {}
    for nombre in nombres_farmacias:
        datos_farm = precios.get(nombre, {})
        pf = datos_farm.get("Precio_Final", float('inf'))
        # Limpieza básica de precio
        try:
            pf = float(pf)
        except:
            pf = float('inf')
            
        if pf and pf > 0 and pf != float('inf'):
            precios_validos[nombre] = pf
        else:
            precios_validos[nombre] = float('inf')

    # Encontrar el menor precio
    farmacias_con_precio = {n: p for n, p in precios_validos.items() if p != float('inf')}

    if len(farmacias_con_precio) == 0:
        v["Ganador"] = "Sin precio"
        v["MejorPrecio"] = 0
    elif len(farmacias_con_precio) == 1:
        unica = list(farmacias_con_precio.keys())[0]
        v["Ganador"] = f"Exclusivo {unica.replace('_', ' ')}"
        v["MejorPrecio"] = farmacias_con_precio[unica]
    else:
        menor_precio = min(farmacias_con_precio.values())
        ganadores = [n for n, p in farmacias_con_precio.items() if p == menor_precio]

        if len(ganadores) > 1:
            v["Ganador"] = "Empate"
        else:
            v["Ganador"] = ganadores[0].replace("_", " ")

        v["MejorPrecio"] = menor_precio

    # Calcular diferencia porcentual entre el más barato y el más caro
    if len(farmacias_con_precio) >= 2:
        precio_min = min(farmacias_con_precio.values())
        precio_max = max(farmacias_con_precio.values())
        if precio_max > 0 and precio_min != precio_max:
            v["Diferencia_Porcentual"] = round(((precio_max - precio_min) / precio_max) * 100, 1)
        else:
            v["Diferencia_Porcentual"] = 0
    else:
        v["Diferencia_Porcentual"] = 0

    # Cantidad de farmacias donde está disponible
    v["Disponible_En"] = len(farmacias_con_precio)

    lista_final.append(v)

# --- Guardar JSON para dashboard ---
os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

# Datos adicionales para el dashboard
data_dashboard = {
    "ultima_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "productos": lista_final
}

# Limpiar NaN/Inf del diccionario para evitar JSON inválido
import math
def clean_nans(obj):
    if isinstance(obj, list):
        return [clean_nans(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

data_limpia = clean_nans(data_dashboard)

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(data_limpia, f, ensure_ascii=False, indent=4)

print(f"Consolidación exitosa. JSON guardado en: {OUTPUT_JSON}")

# --- EXPORTAR A EXCEL (tabla comparativa plana) ---
filas_excel = []
for v in lista_final:
    precios = v.get("Precios", {})
    co = precios.get("Central_Oeste", {})
    fa = precios.get("Farmacity", {})
    fo = precios.get("Farmaonline", {})
    ml = precios.get("MercadoLibre", {})

    filas_excel.append({
        "Killer":                       "SÍ" if v.get("Es_Killer") else "NO",
        "EAN":                          v.get("EAN", "N/A"),
        "Nombre":                       v.get("Nombre", ""),
        "Grupo":                        v.get("Grupo", ""),
        "CO - Precio Final":            co.get("Precio_Final", ""),
        "CO - Precio Lista":            co.get("Precio_Lista", ""),
        "CO - Descuento %":             co.get("Descuento", ""),
        "FA - Precio Final":            fa.get("Precio_Final", ""),
        "FA - Precio Lista":            fa.get("Precio_Lista", ""),
        "FA - Descuento %":             fa.get("Descuento", ""),
        "FO - Precio Final":            fo.get("Precio_Final", ""),
        "FO - Precio Lista":            fo.get("Precio_Lista", ""),
        "FO - Descuento %":             fo.get("Descuento", ""),
        "ML - Precio Final":            ml.get("Precio_Final", ""),
        "ML - Precio Lista":            ml.get("Precio_Lista", ""),
        "Ganador":                      v.get("Ganador", ""),
        "Mejor Precio":                 v.get("MejorPrecio", ""),
        "Diferencia %":                 v.get("Diferencia_Porcentual", 0),
        "Link CO":                      co.get("Link", ""),
        "Link FA":                      fa.get("Link", ""),
        "Link FO":                      fo.get("Link", ""),
        "Link ML":                      ml.get("Link", ""),
    })

df_excel = pd.DataFrame(filas_excel)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(CARPETA_RESULTADOS, f"Comparacion_Farmacias_{ts}.xlsx")

with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
    df_excel.to_excel(writer, index=False, sheet_name="Comparación")

    ws = writer.sheets["Comparación"]
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    # --- Estilos de colores ---
    fill_header  = PatternFill("solid", fgColor="1E293B")
    fill_co      = PatternFill("solid", fgColor="DBEAFE")  # azul claro
    fill_fa      = PatternFill("solid", fgColor="FCE7F3")  # rosa claro
    fill_fo      = PatternFill("solid", fgColor="FEF3C7")  # amarillo claro
    fill_ml      = PatternFill("solid", fgColor="DCFCE7")  # verde claro (ML)
    fill_winner  = PatternFill("solid", fgColor="DCFCE7")  # verde claro (Ganador)
    fill_co_win  = PatternFill("solid", fgColor="93C5FD")  # azul ganador
    fill_fa_win  = PatternFill("solid", fgColor="F9A8D4")  # rosa ganador
    fill_fo_win  = PatternFill("solid", fgColor="FCD34D")  # amarillo ganador
    fill_ml_win  = PatternFill("solid", fgColor="4ADE80")  # verde ganador
    font_header  = Font(bold=True, color="F8FAFC")
    font_link    = Font(color="2563EB", underline="single")
    thin_border  = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # Mapeo de columnas (1-indexed)
    col_co_pf = 5;  col_co_pl = 6;  col_co_dc = 7
    col_fa_pf = 8;  col_fa_pl = 9;  col_fa_dc = 10
    col_fo_pf = 11; col_fo_pl = 12; col_fo_dc = 13
    col_ml_pf = 14; col_ml_pl = 15
    col_ganador = 16; col_mejor = 17; col_dif = 18
    col_lk_co = 19; col_lk_fa = 20; col_lk_fo = 21; col_lk_ml = 22

    cols_co = [col_co_pf, col_co_pl, col_co_dc, col_lk_co]
    cols_fa = [col_fa_pf, col_fa_pl, col_fa_dc, col_lk_fa]
    cols_fo = [col_fo_pf, col_fo_pl, col_fo_dc, col_lk_fo]
    cols_ml = [col_ml_pf, col_ml_pl, col_lk_ml]

    # Encabezado
    for cell in ws[1]:
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[1].height = 30

    # Filas de datos
    for row_idx in range(2, ws.max_row + 1):
        ganador_val = ws.cell(row=row_idx, column=col_ganador).value or ""
        killer_val = ws.cell(row=row_idx, column=1).value or ""
        
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            
            if col_idx in cols_co: cell.fill = fill_co
            elif col_idx in cols_fa: cell.fill = fill_fa
            elif col_idx in cols_fo: cell.fill = fill_fo
            elif col_idx in cols_ml: cell.fill = fill_ml
            elif col_idx == col_ganador:
                if "Central" in ganador_val: cell.fill = fill_co_win
                elif "Farmacity" in ganador_val: cell.fill = fill_fa_win
                elif "Farmaonline" in ganador_val: cell.fill = fill_fo_win
                elif "MercadoLibre" in ganador_val: cell.fill = fill_ml_win
                else: cell.fill = fill_winner
            
            if killer_val == "SÍ" and col_idx <= 4:
                cell.font = Font(bold=True, color="047857")

        # Links como hipervínculo
        for label, col_lk_idx in [("CO", col_lk_co), ("FA", col_lk_fa), ("FO", col_lk_fo), ("ML", col_lk_ml)]:
            cell_link = ws.cell(row=row_idx, column=col_lk_idx)
            if cell_link.value and str(cell_link.value).startswith("http"):
                cell_link.hyperlink = str(cell_link.value)
                cell_link.value = f"Ver en {label}"
                cell_link.font = font_link

    # Ancho de columnas
    anchos = [8, 18, 45, 20, 15, 15, 12, 15, 15, 12, 15, 15, 12, 15, 15, 22, 14, 12, 15, 15, 15, 15]
    for i, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho

    ws.freeze_panes = "A2"

print(f"¡Excel comparativo guardado en: {OUTPUT_EXCEL}")

