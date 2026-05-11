import os
import pandas as pd
from glob import glob
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_RESULTADOS = os.path.join(BASE_DIR, "Resultados_scraping")
RUTA_FALLBACK = os.path.join(BASE_DIR, "killers_urls_fallback.xlsx")

def limpiar_string(s):
    return str(s).strip().lower()

def harvest():
    print("--- COSECHANDO LINKS EXITOSOS PARA ACELERAR PRÓXIMAS EJECUCIONES ---")
    
    if not os.path.exists(RUTA_FALLBACK):
        print("No existe el archivo de fallback. No hay nada que actualizar.")
        return

    # 1. Leer el fallback actual
    try:
        df_fallback = pd.read_excel(RUTA_FALLBACK)
    except Exception as e:
        print(f"Error leyendo fallback: {e}")
        return

    # 2. Buscar los últimos resultados de cada farmacia
    archivos = glob(os.path.join(CARPETA_RESULTADOS, "Output_*.xlsx"))
    if not archivos:
        print("No se encontraron archivos de salida en Resultados_scraping.")
        return

    # Agrupar por farmacia y tomar el más reciente
    farmacias_patrones = ["CentralOeste", "Farmacity", "Farmaonline"]
    exitos = []
    
    for patron in farmacias_patrones:
        f_farmacia = sorted([f for f in archivos if patron in f], key=os.path.getmtime, reverse=True)
        if f_farmacia:
            print(f"  -> Leyendo éxitos de: {os.path.basename(f_farmacia[0])}")
            df_ex = pd.read_excel(f_farmacia[0])
            # Normalizar nombres de farmacia para el fallback
            nombre_fb = "Central Oeste" if "Central" in patron else patron
            df_ex['Farmacia_FB'] = nombre_fb
            exitos.append(df_ex[['Farmacia_FB', 'EAN', 'Nombre', 'Link']])

    if not exitos:
        return

    df_todos_exitos = pd.concat(exitos)
    df_todos_exitos = df_todos_exitos.dropna(subset=['Link'])
    
    # 3. Actualizar el fallback
    # Creamos un nuevo dataframe basado en los éxitos para asegurar que tenemos todo
    df_nuevos_links = df_todos_exitos.rename(columns={'Farmacia_FB': 'Farmacia', 'Link': 'URL'})
    
    if os.path.exists(RUTA_FALLBACK):
        df_old = pd.read_excel(RUTA_FALLBACK)
        # Combinamos priorizando lo nuevo pero manteniendo lo que ya estaba si no está en lo nuevo
        df_final = pd.concat([df_old, df_nuevos_links]).drop_duplicates(subset=['Farmacia', 'EAN', 'Nombre'], keep='last')
    else:
        df_final = df_nuevos_links

    df_final.to_excel(RUTA_FALLBACK, index=False)
    print(f"¡Éxito! Se sincronizaron {len(df_final)} links en {os.path.basename(RUTA_FALLBACK)}.")
    print("La próxima ejecución usará estos links directos y será mucho más rápida.")

if __name__ == "__main__":
    harvest()
