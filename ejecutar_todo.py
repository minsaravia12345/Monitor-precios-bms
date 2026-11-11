import subprocess
import sys
import os
import time

def run_script(script_name):
    print(f"\n==================================================\nINICIANDO: {script_name}\n==================================================")
    try:
        # Usamos -u para que el output sea en tiempo real
        process = subprocess.Popen(
            [sys.executable, "-u", script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Leemos el output línea por línea
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode == 0:
            print(f"COMPLETADO: {script_name}")
            return True
        else:
            print(f"ERROR en {script_name}. (Codigo de salida: {process.returncode})")
            return False
    except Exception as e:
        print(f"ERROR al ejecutar {script_name}: {e}")
        return False

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("INICIANDO PIPELINE DE MONITOREO DE PRECIOS MOLINOS (DIA / JUMBO / DISCO / CARREFOUR / VEA)")
    start_time = time.time()

    # Intentar cosechar links de ejecuciones previas para ganar velocidad
    run_script("cosechar_links.py")

    run_script("scraping_dia.py")
    run_script("scraping_jumbo.py")
    run_script("scraping_disco.py")
    run_script("scraping_carrefour.py")
    run_script("scraping_vea.py")
    
    print("\n--------------------------------------------------")
    print("ANALIZANDO FALTANTES...")
    run_script("generar_faltantes.py")
    print("--------------------------------------------------")
    
    exito_consolidador = run_script("consolidar_datos.py")
    
    end_time = time.time()
    print(f"\nPIPELINE FINALIZADO en {round(end_time - start_time, 1)} segundos.")
    
    if exito_consolidador:
        print("\n¡Los datos estan listos!")
        print("-> Revisa 'productos_urls_fallback.xlsx' si hubo productos no encontrados.")
        print("-> Para ver los resultados en el navegador, ejecuta el archivo: ver_dashboard.py")
