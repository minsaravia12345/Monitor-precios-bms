import pandas as pd
import glob
import os

archivos = glob.glob('Resultados_scraping/*.xlsx')
print(f"Verificando {len(archivos)} archivos...")

for f in archivos:
    if os.path.basename(f).startswith('~$'):
        continue
    try:
        # Solo leemos una fila para ir rápido
        pd.read_excel(f, nrows=1)
        # print(f"OK: {f}")
    except Exception as e:
        print(f"CORRUPTO: {f} -> {e}")
