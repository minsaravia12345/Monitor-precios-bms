import os
from glob import glob

import pandas as pd

from scraper_common import ARCHIVO_FALLBACK, ARCHIVO_PRODUCTOS, CARPETA_RESULTADOS, limpiar_ean

RETAILERS = [
    ("Dia", "Dia_VTEX"),
    ("Jumbo", "Jumbo_VTEX"),
    ("Disco", "Disco_VTEX"),
    ("Carrefour", "Carrefour_VTEX"),
    ("Vea", "Vea_VTEX"),
]

print("--- GENERANDO REPORTE DE PRODUCTOS FALTANTES ---")

if not os.path.exists(ARCHIVO_PRODUCTOS):
    print(f"Error: No se encontró {ARCHIVO_PRODUCTOS}. Corré descubrir_catalogo.py primero.")
    raise SystemExit(1)

df_productos = pd.read_excel(ARCHIVO_PRODUCTOS, dtype={"EAN": str})
col_nombre = [c for c in df_productos.columns if "Descripci" in c]
col_nombre = col_nombre[0] if col_nombre else "Nombre"
df_productos["EAN_clean"] = df_productos["EAN"].apply(limpiar_ean)
productos_list = df_productos.to_dict("records")

archivos = glob(os.path.join(CARPETA_RESULTADOS, "*.xlsx"))
archivos = [f for f in archivos if "Comparacion_" not in os.path.basename(f)]

faltantes = []

for nombre_retailer, patron in RETAILERS:
    encontrados = sorted([f for f in archivos if patron in f], reverse=True)
    eans_encontrados = set()

    if encontrados:
        df_ret = pd.read_excel(encontrados[0])
        if "EAN" in df_ret.columns:
            eans_encontrados = {limpiar_ean(e) for e in df_ret["EAN"].astype(str).tolist()}
    else:
        print(f"Advertencia: No hay resultados previos para {nombre_retailer}.")

    count_faltantes = 0
    for p in productos_list:
        ean_k = p["EAN_clean"]
        if ean_k and ean_k not in eans_encontrados:
            faltantes.append(
                {
                    "Retailer": nombre_retailer,
                    "EAN": ean_k,
                    "Nombre": p.get(col_nombre, p.get("Nombre", "")),
                    "URL": "",
                }
            )
            count_faltantes += 1
        elif not ean_k:
            faltantes.append(
                {
                    "Retailer": nombre_retailer,
                    "EAN": "",
                    "Nombre": p.get(col_nombre, p.get("Nombre", "")),
                    "URL": "",
                }
            )
            count_faltantes += 1

    print(f"{nombre_retailer}: {count_faltantes} productos no encontrados automáticamente.")

if faltantes:
    df_faltantes = pd.DataFrame(faltantes)

    if os.path.exists(ARCHIVO_FALLBACK):
        try:
            df_prev = pd.read_excel(ARCHIVO_FALLBACK)
            if "URL" in df_prev.columns and not df_prev.empty:
                df_prev = df_prev.dropna(subset=["URL"])
                df_faltantes = pd.merge(
                    df_faltantes,
                    df_prev[["Retailer", "EAN", "Nombre", "URL"]],
                    on=["Retailer", "EAN", "Nombre"],
                    how="left",
                    suffixes=("", "_prev"),
                )
                if "URL_prev" in df_faltantes.columns:
                    df_faltantes["URL"] = df_faltantes["URL_prev"].combine_first(df_faltantes["URL"])
                    df_faltantes = df_faltantes.drop(columns=["URL_prev"])
        except Exception as e:
            print(f"No se pudieron cargar las URLs previas: {e}")

    with pd.ExcelWriter(ARCHIVO_FALLBACK, engine="openpyxl") as writer:
        df_faltantes.to_excel(writer, index=False, sheet_name="Faltantes")
        ws = writer.sheets["Faltantes"]

        from openpyxl.styles import Font, PatternFill

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="DDDDDD")

        ws.column_dimensions["D"].width = 60
        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 45

        for row in ws.iter_rows(min_row=2, min_col=4, max_col=4):
            for cell in row:
                if not cell.value:
                    cell.fill = PatternFill("solid", fgColor="FFFF00")

    print(f"\nSe generó {ARCHIVO_FALLBACK} con {len(df_faltantes)} registros.")
    print("-> Por favor, abre este archivo, pega las URLs correctas en la columna amarilla y vuelve a ejecutar los scrapers.")
else:
    print("\n¡Excelente! Se encontró el 100% de los productos en todos los retailers.")
    pd.DataFrame(columns=["Retailer", "EAN", "Nombre", "URL"]).to_excel(ARCHIVO_FALLBACK, index=False)
