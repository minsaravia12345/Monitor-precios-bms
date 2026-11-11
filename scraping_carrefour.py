from scraper_common import configurar_salida_utf8, ejecutar_scraper_vtex

configurar_salida_utf8()

if __name__ == "__main__":
    ejecutar_scraper_vtex(
        nombre_retailer="Carrefour",
        filtro_fallback="carrefour",
        base_url="https://www.carrefour.com.ar",
    )
