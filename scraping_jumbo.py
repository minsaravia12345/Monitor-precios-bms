from scraper_common import configurar_salida_utf8, ejecutar_scraper_vtex

configurar_salida_utf8()

if __name__ == "__main__":
    ejecutar_scraper_vtex(
        nombre_retailer="Jumbo",
        filtro_fallback="jumbo",
        base_url="https://www.jumbo.com.ar",
    )
