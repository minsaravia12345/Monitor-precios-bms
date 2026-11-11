import json
import math
import os
import re
from datetime import datetime
from glob import glob

import pandas as pd

from scraper_common import limpiar_ean

# --- CONFIGURACIÓN ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_RESULTADOS = os.path.join(BASE_DIR, "Resultados_scraping")
OUTPUT_JSON = os.path.join(BASE_DIR, "dashboard", "public", "datos_consolidados.json")
RUTA_PRODUCTOS = os.path.join(BASE_DIR, "Productos Molinos.xlsx")

# Retailers soportados: (nombre interno, patron que usa cada archivo Output_*.xlsx)
RETAILERS = [
    ("Dia", "Dia_VTEX"),
    ("Jumbo", "Jumbo_VTEX"),
    ("Disco", "Disco_VTEX"),
    ("Carrefour", "Carrefour_VTEX"),
    ("Vea", "Vea_VTEX"),
]
NOMBRES_RETAILERS = [r[0] for r in RETAILERS]

print("--- INICIANDO CONSOLIDACIÓN ---")

archivos = glob(os.path.join(CARPETA_RESULTADOS, "*.xlsx"))
archivos = [f for f in archivos if "Comparacion_" not in os.path.basename(f) and not os.path.basename(f).startswith("~$")]

dfs = {}
for nombre_retailer, patron in RETAILERS:
    encontrados = sorted([f for f in archivos if patron in f], reverse=True)
    for f_path in encontrados:
        try:
            df = pd.read_excel(f_path)
            df["Retailer"] = nombre_retailer
            dfs[nombre_retailer] = df
            print(f"Cargado {nombre_retailer}: {os.path.basename(f_path)} ({len(df)} productos)")
            break
        except Exception as e:
            print(f"Advertencia: El archivo {os.path.basename(f_path)} está corrupto o es inválido. Saltando... Error: {e}")
            continue

# --- CARGAR EXCEL SEMILLA (productos a trackear) ---
df_productos = pd.DataFrame()
if os.path.exists(RUTA_PRODUCTOS):
    try:
        df_productos = pd.read_excel(RUTA_PRODUCTOS, dtype={"EAN": str})
        df_productos["EAN"] = df_productos["EAN"].apply(limpiar_ean)
        print(f"Cargado Excel de productos: {len(df_productos)} productos a trackear")
    except Exception as e:
        print(f"Error leyendo el Excel de productos (¿está abierto en otro programa?): {e}")
else:
    print(f"No se encontró el archivo en {RUTA_PRODUCTOS}")

if not dfs:
    print("No se encontraron archivos de scraping. Abortando.")
    raise SystemExit(0)

# --- INDEXAR RESULTADOS DEL SCRAPING POR EAN/NOMBRE ---
df_total = pd.concat(list(dfs.values()), ignore_index=True)
scraping_index = {}

for _, row in df_total.iterrows():
    ean_val = limpiar_ean(row.get("EAN_Original", row.get("EAN", ""))).lower()
    nombre_val = str(row.get("Nombre_Original", row.get("Nombre", ""))).lower().strip()

    claves = []
    if ean_val and ean_val != "nan":
        claves.append(ean_val)
    if nombre_val:
        claves.append(nombre_val)

    for c in claves:
        if c not in scraping_index:
            scraping_index[c] = {"Precios": {}}

        promocion = row.get("Promocion", "")
        scraping_index[c]["Precios"][row["Retailer"]] = {
            "Precio_Final": row["Precio_Final"],
            "Precio_Lista": row["Precio_Lista"],
            "Descuento": row.get("Porcentaje_Oferta", 0),
            "Stock": row.get("Stock", "Con Stock"),
            "Promocion": promocion if isinstance(promocion, str) else "",
            "Link": row.get("Link", "#"),
        }

# --- CONSTRUIR LISTA FINAL BASADA EN EL EXCEL DE PRODUCTOS ---
lista_final = []

if not df_productos.empty:
    col_nombre_k = [c for c in df_productos.columns if "Descripci" in c]
    col_nombre_k = col_nombre_k[0] if col_nombre_k else "Nombre"

    for idx, row in df_productos.iterrows():
        ean_k = limpiar_ean(row.get("EAN", ""))
        nombre_k = str(row.get(col_nombre_k, row.get("Nombre", ""))).strip()
        marca_k = str(row.get("Marca", "")).strip() or "Molinos"

        clave_ean = ean_k.lower() if ean_k and ean_k != "nan" else None
        clave_nom = nombre_k.lower().strip()

        datos_scraping = None
        if clave_ean and clave_ean in scraping_index:
            datos_scraping = scraping_index[clave_ean]
        elif clave_nom and clave_nom in scraping_index:
            datos_scraping = scraping_index[clave_nom]

        precios_encontrados = datos_scraping["Precios"] if datos_scraping else {}

        producto_consolidado = {
            "Id": f"row_{idx}",
            "EAN": ean_k,
            "Nombre": nombre_k,
            "Grupo": marca_k,
            "Es_Killer": False,
            "Precios": precios_encontrados,
        }

        # --- Determinar ganador para esta fila ---
        precios_validos = {}
        for nombre_retailer in NOMBRES_RETAILERS:
            d_retailer = precios_encontrados.get(nombre_retailer, {})
            pf = d_retailer.get("Precio_Final", float("inf"))
            stk = str(d_retailer.get("Stock", "")).strip().lower()

            if stk == "sin stock" or str(pf).strip().lower() == "sin stock":
                precios_validos[nombre_retailer] = float("inf")
            else:
                try:
                    pf = float(pf)
                    precios_validos[nombre_retailer] = pf if pf > 0 else float("inf")
                except (TypeError, ValueError):
                    precios_validos[nombre_retailer] = float("inf")

        con_precio = {n: p for n, p in precios_validos.items() if p != float("inf")}

        if not con_precio:
            producto_consolidado["Ganador"] = "Sin precio"
            producto_consolidado["MejorPrecio"] = 0
        elif len(con_precio) == 1:
            unico = list(con_precio.keys())[0]
            producto_consolidado["Ganador"] = f"Exclusivo {unico}"
            producto_consolidado["MejorPrecio"] = con_precio[unico]
        else:
            min_p = min(con_precio.values())
            ganadores = [n for n, p in con_precio.items() if p == min_p]
            producto_consolidado["Ganador"] = "Empate" if len(ganadores) > 1 else ganadores[0]
            producto_consolidado["MejorPrecio"] = min_p

            max_p = max(con_precio.values())
            producto_consolidado["Diferencia_Porcentual"] = round(((max_p - min_p) / max_p) * 100, 1) if max_p > 0 else 0

        producto_consolidado["Disponible_En"] = len(con_precio)
        lista_final.append(producto_consolidado)
else:
    print("ERROR: No hay lista base de productos para procesar.")

# --- Guardar JSON para dashboard ---
os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
data_dashboard = {
    "ultima_actualizacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "productos": lista_final,
}


def clean_nans(obj):
    if isinstance(obj, list):
        return [clean_nans(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(clean_nans(data_dashboard), f, ensure_ascii=False, indent=4)

print(f"Consolidación exitosa. JSON guardado en: {OUTPUT_JSON}")

# --- EXPORTAR A EXCEL (tabla comparativa, generica para N retailers) ---
filas_excel = []
for v in lista_final:
    precios = v.get("Precios", {})
    fila = {"EAN": v.get("EAN", "N/A"), "Nombre": v.get("Nombre", ""), "Marca": v.get("Grupo", "")}
    for nombre_retailer in NOMBRES_RETAILERS:
        d = precios.get(nombre_retailer, {})
        fila[f"{nombre_retailer} - Precio Final"] = d.get("Precio_Final", "")
        fila[f"{nombre_retailer} - Precio Lista"] = d.get("Precio_Lista", "")
        fila[f"{nombre_retailer} - Descuento %"] = d.get("Descuento", "")
        fila[f"{nombre_retailer} - Promocion"] = d.get("Promocion", "")
        fila[f"{nombre_retailer} - Stock"] = d.get("Stock", "No Encontrado")
        fila[f"{nombre_retailer} - Link"] = d.get("Link", "")
    fila["Ganador"] = v.get("Ganador", "")
    fila["Mejor Precio"] = v.get("MejorPrecio", "")
    fila["Diferencia %"] = v.get("Diferencia_Porcentual", 0)
    filas_excel.append(fila)

df_excel = pd.DataFrame(filas_excel)

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_EXCEL = os.path.join(CARPETA_RESULTADOS, f"Comparacion_Retailers_{ts}.xlsx")

with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
    df_excel.to_excel(writer, index=False, sheet_name="Comparación")

    ws = writer.sheets["Comparación"]
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    PALETA_RETAILERS = {
        "Dia": "FCE7E7",
        "Jumbo": "DCFCE7",
        "Disco": "FEF3C7",
        "Carrefour": "DBEAFE",
        "Vea": "EDE9FE",
    }

    fill_header = PatternFill("solid", fgColor="1E293B")
    font_header = Font(bold=True, color="F8FAFC")
    font_link = Font(color="2563EB", underline="single")
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    columnas = list(df_excel.columns)
    col_idx_por_nombre = {nombre: i + 1 for i, nombre in enumerate(columnas)}

    for cell in ws[1]:
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border
    ws.row_dimensions[1].height = 30

    for row_idx in range(2, ws.max_row + 1):
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=False)

        for nombre_retailer in NOMBRES_RETAILERS:
            color = PALETA_RETAILERS.get(nombre_retailer, "F1F5F9")
            for sufijo in ("Precio Final", "Precio Lista", "Descuento %", "Promocion", "Stock"):
                col_idx = col_idx_por_nombre.get(f"{nombre_retailer} - {sufijo}")
                if col_idx:
                    ws.cell(row=row_idx, column=col_idx).fill = PatternFill("solid", fgColor=color)

            col_stock = col_idx_por_nombre.get(f"{nombre_retailer} - Stock")
            if col_stock:
                cell_stock = ws.cell(row=row_idx, column=col_stock)
                if cell_stock.value == "Con Stock":
                    cell_stock.font = Font(color="047857", bold=True)
                elif cell_stock.value == "Sin Stock":
                    cell_stock.font = Font(color="DC2626", bold=True)
                else:
                    cell_stock.font = Font(color="9CA3AF")

            col_link = col_idx_por_nombre.get(f"{nombre_retailer} - Link")
            if col_link:
                cell_link = ws.cell(row=row_idx, column=col_link)
                if cell_link.value and str(cell_link.value).startswith("http"):
                    cell_link.hyperlink = str(cell_link.value)
                    cell_link.value = f"Ver en {nombre_retailer}"
                    cell_link.font = font_link

    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 45
    ws.column_dimensions["C"].width = 14
    for nombre_retailer in NOMBRES_RETAILERS:
        for sufijo in ("Precio Final", "Precio Lista", "Descuento %", "Promocion", "Stock", "Link"):
            col_idx = col_idx_por_nombre.get(f"{nombre_retailer} - {sufijo}")
            if col_idx:
                ancho = 28 if sufijo == "Promocion" else 15
                ws.column_dimensions[get_column_letter(col_idx)].width = ancho

    ws.freeze_panes = "A2"

print(f"¡Excel comparativo guardado en: {OUTPUT_EXCEL}")
