import os
from glob import glob

import pandas as pd

from scraper_common import ARCHIVO_FALLBACK, CARPETA_RESULTADOS

RETAILERS_PATRONES = ["Dia", "Jumbo", "Disco", "Carrefour", "Vea"]


def harvest():
    print("--- COSECHANDO LINKS EXITOSOS PARA ACELERAR PRÓXIMAS EJECUCIONES ---")

    if not os.path.exists(ARCHIVO_FALLBACK):
        print("No existe el archivo de fallback. No hay nada que actualizar.")
        return

    archivos = glob(os.path.join(CARPETA_RESULTADOS, "Output_*.xlsx"))
    if not archivos:
        print("No se encontraron archivos de salida en Resultados_scraping.")
        return

    exitos = []
    for patron in RETAILERS_PATRONES:
        f_retailer = sorted([f for f in archivos if patron in f], key=os.path.getmtime, reverse=True)
        if f_retailer:
            print(f"  -> Leyendo éxitos de: {os.path.basename(f_retailer[0])}")
            df_ex = pd.read_excel(f_retailer[0])
            df_ex["Retailer"] = patron
            exitos.append(df_ex[["Retailer", "EAN", "Nombre", "Link"]])

    if not exitos:
        return

    df_todos_exitos = pd.concat(exitos)
    df_todos_exitos = df_todos_exitos.dropna(subset=["Link"])
    df_nuevos_links = df_todos_exitos.rename(columns={"Link": "URL"})

    df_old = pd.read_excel(ARCHIVO_FALLBACK)
    df_final = pd.concat([df_old, df_nuevos_links]).drop_duplicates(subset=["Retailer", "EAN", "Nombre"], keep="last")

    df_final.to_excel(ARCHIVO_FALLBACK, index=False)
    print(f"¡Éxito! Se sincronizaron {len(df_final)} links en {os.path.basename(ARCHIVO_FALLBACK)}.")
    print("La próxima ejecución usará estos links directos y será mucho más rápida.")


if __name__ == "__main__":
    harvest()
