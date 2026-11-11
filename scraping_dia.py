from scraper_common import configurar_salida_utf8, ejecutar_scraper_vtex

configurar_salida_utf8()

if __name__ == "__main__":
    ejecutar_scraper_vtex(
        nombre_retailer="Dia",
        filtro_fallback="dia",
        base_url="https://diaonline.supermercadosdia.com.ar",
    )
