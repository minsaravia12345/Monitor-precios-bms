"""
Arma el Excel semilla "Productos Molinos.xlsx" rastreando las marcas de
Molinos Rio de la Plata en los 5 retailers (todos VTEX), en vez de depender
de una lista curada a mano como "Killers evento.xlsx". Cada scraper de
retailer despues busca, producto por producto, los EAN que este script
encontro.

Correr una sola vez (o cada tanto para detectar productos nuevos); no hace
falta correrlo antes de cada scraping diario.
"""

import time
import urllib.parse

import pandas as pd

from scraper_common import ARCHIVO_PRODUCTOS, configurar_salida_utf8, crear_sesion, limpiar_ean

configurar_salida_utf8()

# Marcas de Molinos Rio de la Plata (verificado: La Nacion 2024, iProfesional
# sobre la compra de NotCo). Conviene revisar molinos.com.ar si esta lista
# necesita actualizarse: el portfolio cambia con adquisiciones.
MARCAS_MOLINOS = [
    "Gallo",
    "Lucchetti",
    "Matarazzo",
    "Blancaflor",
    "Cocinero",
    "Lira",
    "Exquisita",
    "La Salteña",
    "Sibarita",
    "Preferido",
    "Cruz de Malta",
    "Granja del Sol",
    "Don Vicente",
]

RETAILERS = [
    ("Dia", "https://diaonline.supermercadosdia.com.ar"),
    ("Jumbo", "https://www.jumbo.com.ar"),
    ("Disco", "https://www.disco.com.ar"),
    ("Carrefour", "https://www.carrefour.com.ar"),
    ("Vea", "https://www.vea.com.ar"),
]

TAMANO_PAGINA = 50  # maximo real que VTEX permite por pagina (_to > 49 da 400)
TOPE_SEGURIDAD = 1000  # por marca+retailer, para no entrar en loop ante una respuesta rara
PAUSA_ENTRE_REQUESTS = 0.3


def buscar_marca(session, base_url, marca):
    """Pagina hasta agotar TODOS los resultados reales de esta marca en este
    retailer (usando el header 'resources: desde-hasta/total' de VTEX para
    saber cuando parar), no solo las primeras 1-2 paginas. Antes el scraper
    se quedaba con, como mucho, 100 productos por marca y retailer aunque el
    catalogo real tuviera 300-400 (confirmado en vivo: 'gallo' solo en
    Jumbo son 342 resultados)."""
    productos = {}
    desde = 0
    total_conocido = None

    while desde < TOPE_SEGURIDAD:
        hasta = desde + TAMANO_PAGINA - 1
        url = f"{base_url}/api/catalog_system/pub/products/search?ft={urllib.parse.quote(marca)}&_from={desde}&_to={hasta}"
        try:
            res = session.get(url, timeout=15)
        except Exception as e:
            print(f"     [!] Error de red: {e}")
            break

        if res.status_code not in (200, 206):
            break

        if total_conocido is None:
            recurso = res.headers.get("resources", "")
            if "/" in recurso:
                try:
                    total_conocido = int(recurso.rsplit("/", 1)[-1])
                except ValueError:
                    total_conocido = None

        try:
            data = res.json()
        except ValueError:
            break

        if not data:
            break

        for item in data:
            items = item.get("items") or []
            if not items:
                continue
            ean = limpiar_ean(items[0].get("ean", ""))
            if not ean:
                continue
            marca_vtex = str(item.get("brand", "")).strip()
            # Solo aceptamos el resultado si la marca que VTEX le asigno al
            # producto efectivamente coincide con la marca de Molinos que
            # estamos buscando (evita ruido de coincidencias de texto
            # casuales con otras marcas que no son de Molinos).
            if marca.lower() not in marca_vtex.lower() and marca_vtex.lower() not in marca.lower():
                continue
            productos[ean] = {
                "EAN": ean,
                "Descripcion": item.get("productName", ""),
                "Marca": marca,
            }

        desde += TAMANO_PAGINA
        if total_conocido is not None and desde >= total_conocido:
            break
        if len(data) < TAMANO_PAGINA:
            break

        time.sleep(PAUSA_ENTRE_REQUESTS)

    return productos


def main():
    print("--- DESCUBRIENDO CATALOGO DE PRODUCTOS MOLINOS ---")
    session = crear_sesion()

    catalogo = {}
    for marca in MARCAS_MOLINOS:
        print(f"\n-> Marca: {marca}")
        for nombre_retailer, base_url in RETAILERS:
            encontrados = buscar_marca(session, base_url, marca)
            nuevos = sum(1 for ean in encontrados if ean not in catalogo)
            catalogo.update(encontrados)
            print(f"   {nombre_retailer}: {len(encontrados)} productos ({nuevos} nuevos)")
            time.sleep(PAUSA_ENTRE_REQUESTS)

    if not catalogo:
        print("\nNo se encontraron productos. No se genero el Excel.")
        return

    df = pd.DataFrame(catalogo.values()).sort_values(["Marca", "Descripcion"])
    df.to_excel(ARCHIVO_PRODUCTOS, index=False)
    print(f"\n¡Éxito! {len(df)} productos únicos guardados en: {ARCHIVO_PRODUCTOS}")
    print("\nResumen por marca:")
    for marca, cantidad in df["Marca"].value_counts().items():
        print(f"  - {marca}: {cantidad}")


if __name__ == "__main__":
    main()
