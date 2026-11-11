"""
Utilidades compartidas por los scrapers de Dia, Jumbo, Disco, Carrefour y Vea.

Centraliza: carga del Excel de productos a trackear, carga de URLs de
fallback/prioridad, normalizacion de EAN, parseo de precios en formato
argentino, una sesion HTTP con reintentos automaticos, un motor generico de
busqueda VTEX (las 5 cadenas corren sobre VTEX) y el guardado de resultados
con resumen por metodo de match. Mantener esta logica en un solo lugar evita
que un bug exista en un retailer y no en los otros.
"""

import os
import re
import sys
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_PRODUCTOS = os.path.join(BASE_DIR, "Productos Molinos.xlsx")
ARCHIVO_FALLBACK = os.path.join(BASE_DIR, "productos_urls_fallback.xlsx")
CARPETA_RESULTADOS = os.path.join(BASE_DIR, "Resultados_scraping")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def configurar_salida_utf8():
    """Evita que un print() con tildes/ñ reviente el script en una consola
    de Windows configurada con una codepage que no sea UTF-8 (cp1252, etc.)."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def crear_sesion(user_agent=USER_AGENT, total_reintentos=3, backoff=0.6):
    """Sesion de requests con reintentos automaticos ante timeouts, errores
    de conexion y respuestas 5xx/429. Antes cada fallo transitorio (muy
    comunes en scraping) perdia el producto para siempre en esa corrida."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3",
        }
    )
    retry = Retry(
        total=total_reintentos,
        connect=total_reintentos,
        read=total_reintentos,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def limpiar_ean(valor):
    """Normaliza un EAN que Excel puede entregar como notacion cientifica
    (7.50955E+12) o como float con '.0' al final, a un string de solo digitos."""
    texto = str(valor).strip()
    if texto.lower() == "nan":
        return ""
    if "e" in texto.lower() or "." in texto:
        try:
            texto = format(float(texto), ".0f")
        except (ValueError, OverflowError):
            pass
    return re.sub(r"\.0$", "", texto).strip()


def limpiar_precio_ar(texto):
    """Parsea un precio en formato argentino: '.' como separador de miles,
    ',' como separador decimal (ambos opcionales). Devuelve el precio entero
    en pesos, sin decimales.

    Antes esta funcion asumia que, si el texto tenia un '.' o una ',', los
    ultimos 2 digitos eran siempre centavos a descartar. Eso es correcto para
    '$ 13.194,00' pero rompe '$ 13.194' (sin centavos): el resultado pasaba a
    ser 131 en vez de 13194, un error de ~100x. Esta version separa
    explicitamente la parte entera de la decimal usando la coma como pivote.
    """
    if not texto:
        return 0
    texto = str(texto).strip()
    solo_validos = re.sub(r"[^\d,.]", "", texto)
    if not solo_validos:
        return 0

    if "," in solo_validos:
        parte_entera = solo_validos.split(",")[0]
    else:
        parte_entera = solo_validos

    parte_entera = parte_entera.replace(".", "")
    if not parte_entera:
        return 0

    try:
        return int(parte_entera)
    except ValueError:
        return 0


def slug_producto_vtex(url):
    """Extrae el slug de una URL de producto VTEX (.../mi-producto/p) para
    reconstruir la URL de la API de busqueda. Antes se usaba `"/p" in url`
    como condicion, lo que da falsos positivos con categorias como
    '/perfumeria/...' (empiezan con '/p'); ahora se usa endswith, que es
    la forma correcta de detectar el sufijo real de producto de VTEX."""
    url = url.strip()
    if url.endswith("/p"):
        slug = url.rstrip("/").split("/")[-2]
    elif "/p/" in url:
        slug = url.split("/p/")[0].rstrip("/").split("/")[-1]
    else:
        slug = url.rstrip("/").split("/")[-1]
    return slug


PALABRAS_VACIAS = {"x", "de", "del", "la", "el", "los", "las", "con", "sin", "y", "en"}

_RE_CANTIDAD = re.compile(
    r"\b(x)?\s*\d+[.,]?\d*\s*(ml|mg|gr|g|kg|cc|cm|un|u|unid|comp|caps|c[aá]ps|tab|sobres?|dosis)\b",
    re.IGNORECASE,
)


def limpiar_tokens_cantidad(nombre):
    """Saca tokens de cantidad/presentacion ('X 100 ML', '20 COMP', etc.) de
    un nombre de producto. Dos sitios distintos casi nunca escriben la
    presentacion exactamente igual (100ml vs 100 ml vs x100ml), y esos
    tokens son justamente lo que mas hace fallar una busqueda de texto
    completo por nombre: el motor de busqueda del sitio exige que calcen
    TODAS las palabras. Buscar sin ellos sube el recall sin perder
    precision, porque la validacion final sigue siendo por EAN o por
    similitud de palabras."""
    texto = _RE_CANTIDAD.sub(" ", nombre)
    texto = re.sub(r"\s{2,}", " ", texto).strip()
    return texto


def variantes_busqueda_nombre(nombre_limpio):
    """Arma una escalera de variantes de busqueda por nombre, de la mas
    especifica a la mas general: nombre completo, nombre sin cantidad, y
    recortes progresivos de esa version limpia a 4, 3 y 2 palabras. Cada
    scraper prueba estas variantes en orden y se queda con la primera que
    de un resultado valido, asi que en la mayoria de los casos (EAN o
    nombre completo calzan) no se pagan los intentos extra: el costo real
    solo se paga para el puñado de productos que hoy no se encuentran."""
    sin_cantidad = limpiar_tokens_cantidad(nombre_limpio)
    palabras_base = sin_cantidad.split() if sin_cantidad else nombre_limpio.split()

    variantes = [nombre_limpio]
    if sin_cantidad and sin_cantidad.lower() != nombre_limpio.lower():
        variantes.append(sin_cantidad)
    for largo in (4, 3, 2):
        if largo < len(palabras_base):
            variantes.append(" ".join(palabras_base[:largo]))

    vistos = set()
    unicas = []
    for variante in variantes:
        clave = variante.lower()
        if variante and clave not in vistos:
            vistos.add(clave)
            unicas.append(variante)
    return unicas


def variantes_ean(ean):
    """Un EAN exportado desde Excel pierde a veces un cero a la izquierda
    (lo trata como numero), o viene en UPC-12 en vez de EAN-13. Probar estas
    variantes ademas del valor tal cual recupera productos cuyo EAN en el
    sitio no es byte a byte igual al del Excel."""
    if not ean or not ean.isdigit():
        return [ean] if ean else []

    variantes = [ean]
    if not ean.startswith("0"):
        variantes.append("0" + ean)
    elif len(ean) > 1:
        sin_cero = ean.lstrip("0")
        if sin_cero:
            variantes.append(sin_cero)

    vistos = set()
    unicas = []
    for v in variantes:
        if v not in vistos:
            vistos.add(v)
            unicas.append(v)
    return unicas


def _normalizar_para_score(texto):
    texto = str(texto).lower()
    texto = re.sub(r"[^a-z0-9áéíóúñ\s]", " ", texto)
    # separa numero y unidad pegados ("50ml" -> "50 ml", "spf50" -> "spf 50"):
    # sin esto, "50ml" y "50 ml" (la misma cantidad, escrita distinto en dos
    # sitios) no comparten ningun token y el score sale mas bajo de lo que
    # deberia, al punto de empatar con un candidato que en realidad es otro
    # producto de la misma linea.
    texto = re.sub(r"(\d)([a-záéíóúñ])", r"\1 \2", texto)
    texto = re.sub(r"([a-záéíóúñ])(\d)", r"\1 \2", texto)
    return {p for p in texto.split() if p not in PALABRAS_VACIAS}


def puntaje_similitud(nombre_objetivo, nombre_candidato):
    """Mide que fraccion de las palabras significativas del nombre que
    buscamos aparece en el nombre del producto candidato. 1.0 = todas las
    palabras del objetivo estan en el candidato."""
    objetivo = _normalizar_para_score(nombre_objetivo)
    if not objetivo:
        return 0.0
    candidato = _normalizar_para_score(nombre_candidato)
    if not candidato:
        return 0.0
    return len(objetivo & candidato) / len(objetivo)


def elegir_mejor_candidato(candidatos, nombre_objetivo, obtener_nombre, umbral=0.45):
    """De una lista de resultados de busqueda (sin EAN para validar
    exactamente), elige el que mas se parezca por palabras al nombre que
    buscamos, en vez de asumir a ciegas que el primer resultado del motor
    de busqueda del sitio es el correcto. Devuelve None si ninguno supera
    el umbral de similitud."""
    mejor, mejor_score = None, 0.0
    for candidato in candidatos:
        score = puntaje_similitud(nombre_objetivo, obtener_nombre(candidato))
        if score > mejor_score:
            mejor_score, mejor = score, candidato
    return mejor if mejor_score >= umbral else None


def preparar_nombre_busqueda(nombre_k):
    """A partir del nombre crudo de una fila del Excel de productos, arma
    las variantes de nombre usadas como estrategias de busqueda: nombre
    completo limpio, nombre corto (3 primeras palabras) y nombre 'seguro'
    (sin palabras con caracteres de reemplazo tipicos de un Excel mal
    codificado)."""
    nombre_limpio = re.sub(r"^\d+\s*-\s*", "", nombre_k).strip()
    nombre_corto = " ".join(nombre_limpio.split()[:3])

    caracteres_corruptos = ("�", "?", "�")
    palabras_limpias = [
        p for p in nombre_limpio.split() if not any(c in p for c in caracteres_corruptos)
    ]
    nombre_seguro = " ".join(palabras_limpias[:3])

    return nombre_limpio, nombre_corto, nombre_seguro


def cargar_productos(ruta=ARCHIVO_PRODUCTOS):
    """Carga y normaliza el Excel maestro de productos a trackear (columnas
    EAN, Descripcion/Nombre y opcionalmente Marca). Devuelve una lista de
    dicts listos para que cualquier scraper itere sobre ellos."""
    if not os.path.exists(ruta):
        print(f"Archivo de productos no encontrado: {ruta}")
        return []

    df = pd.read_excel(ruta, dtype={"EAN": str})
    columnas_nombre = [c for c in df.columns if "Descripci" in c]
    col_nombre = columnas_nombre[0] if columnas_nombre else "Nombre"

    productos = []
    for _, row in df.iterrows():
        ean_k = limpiar_ean(row.get("EAN", ""))
        nombre_k = str(row.get(col_nombre, row.get("Nombre", ""))).strip()
        if nombre_k.lower() == "nan":
            nombre_k = ""

        if not ean_k and not nombre_k:
            continue

        sku_match = re.search(r"^(\d{5,8})", nombre_k)
        sku_id = sku_match.group(1) if sku_match else None
        nombre_limpio, nombre_corto, nombre_seguro = preparar_nombre_busqueda(nombre_k)

        productos.append(
            {
                "ean": ean_k,
                "sku": sku_id,
                "marca": str(row.get("Marca", "")).strip(),
                "nombre_raw": nombre_k,
                "nombre_limpio": nombre_limpio,
                "nombre_corto": nombre_corto,
                "nombre_seguro": nombre_seguro,
            }
        )

    return productos


def cargar_urls_prioridad(nombre_retailer_filtro, ruta=ARCHIVO_FALLBACK):
    """Devuelve un dict {ean_nombre: url} con las URLs ya confirmadas para
    este retailer en corridas anteriores (ya sea por fallback manual o
    cosechadas de un scraping previo exitoso)."""
    urls_prioridad = {}
    if not os.path.exists(ruta):
        return urls_prioridad

    try:
        df_fb = pd.read_excel(ruta)
        if df_fb.empty or "Retailer" not in df_fb.columns:
            return urls_prioridad
        df_fb = df_fb[df_fb["Retailer"].str.lower().str.contains(nombre_retailer_filtro, na=False)]
        for _, row in df_fb.iterrows():
            ean_fb = str(row.get("EAN", "")).strip()
            nom_fb = str(row.get("Nombre", "")).strip()
            url_fb = str(row.get("URL", "")).strip()
            if url_fb and url_fb != "nan":
                urls_prioridad[f"{ean_fb}_{nom_fb}"] = url_fb
    except Exception as e:
        print(f"[!] No se pudieron cargar URLs de prioridad: {e}")

    return urls_prioridad


def cargar_fallback_pendientes(nombre_retailer_filtro, eans_ya_encontrados, ruta=ARCHIVO_FALLBACK):
    """Devuelve las filas del Excel de fallback para este retailer cuyo EAN
    todavia no fue resuelto en la Fase 1 (busqueda automatica)."""
    if not os.path.exists(ruta):
        return []

    try:
        df_fb = pd.read_excel(ruta)
    except Exception as e:
        print(f"[!] No se pudo leer el archivo de fallback: {e}")
        return []

    if df_fb.empty or "Retailer" not in df_fb.columns or "URL" not in df_fb.columns:
        return []

    df_fb = df_fb[df_fb["Retailer"].str.lower().str.contains(nombre_retailer_filtro, na=False)]

    pendientes = []
    for _, row in df_fb.iterrows():
        ean = limpiar_ean(row.get("EAN", ""))
        if ean and ean in eans_ya_encontrados:
            continue
        url_fb = str(row.get("URL", "")).strip()
        if not url_fb or url_fb == "nan":
            continue
        pendientes.append(
            {
                "ean": ean,
                "url": url_fb,
                "nombre_original": str(row.get("Nombre", f"Producto Fallback {ean}")),
            }
        )
    return pendientes


def guardar_resultados(productos, nombre_archivo_prefijo):
    """Guarda los productos extraidos en Resultados_scraping/, deduplicados,
    e imprime un resumen de cuantos se encontraron por cada metodo de
    busqueda (EAN, Nombre, URL de fallback, etc.) para poder confiar en la
    calidad del match, no solo en la cantidad."""
    if not productos:
        print("\nNo se extrajeron datos.")
        return None

    df_out = pd.DataFrame(productos)
    df_out = df_out.drop_duplicates(subset=["EAN", "Nombre"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    path = os.path.join(CARPETA_RESULTADOS, f"Output_{nombre_archivo_prefijo}_{ts}.xlsx")
    df_out.to_excel(path, index=False)

    print(f"\n¡Éxito! Guardados {len(df_out)} productos en: {path}")

    if "Metodo_Match" in df_out.columns:
        print("\nResumen por metodo de match:")
        for metodo, cantidad in df_out["Metodo_Match"].value_counts().items():
            print(f"  - {metodo}: {cantidad}")

    return path


# ============================================================
# Motor generico de scraping VTEX
#
# Dia, Jumbo, Disco, Carrefour y Vea corren las 5 sobre la plataforma VTEX,
# con exactamente la misma forma de API (confirmado en vivo contra las 5).
# En vez de 5 archivos casi identicos, cada scraper de retailer es un
# wrapper de ~10 lineas que llama a `ejecutar_scraper_vtex` con su propia
# URL base y nombre.
# ============================================================


def vtex_buscar_json_lista(session, url):
    try:
        res = session.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"     [!] Error de red: {e}")
        return []

    if res.status_code not in (200, 206):
        return []

    try:
        data = res.json()
    except ValueError:
        return []

    return data or []


def vtex_buscar_json(session, url):
    lista = vtex_buscar_json_lista(session, url)
    return lista[0] if lista else None


def vtex_buscar_por_nombre(session, url, nombre_objetivo):
    """Una busqueda de texto libre devuelve varios candidatos; en vez de
    asumir que el primero del ranking de VTEX es el correcto, elegimos el
    que mas se parece por palabras al nombre que buscamos."""
    lista = vtex_buscar_json_lista(session, url)
    if not lista:
        return None
    if len(lista) == 1:
        return lista[0]
    return elegir_mejor_candidato(lista, nombre_objetivo, lambda item: item.get("productName", "")) or lista[0]


def vtex_elegir_sku(res_item, ean_target):
    """De todas las variantes (SKUs) del producto encontrado, elige la que
    coincide con el EAN que estabamos buscando. Si no hay EAN para validar
    (busqueda por nombre), toma la primera variante disponible."""
    items = res_item.get("items") or []
    if not items:
        return None, ""

    if ean_target:
        for item in items:
            if str(item.get("ean", "")).strip() == ean_target:
                return item, ean_target
        return None, ""

    primero = items[0]
    return primero, str(primero.get("ean", "")).strip()


def vtex_extraer_oferta(sku_item):
    """Convierte la oferta comercial de VTEX en los campos que usa el
    dashboard. Devuelve None si el SKU no tiene seller/oferta disponible."""
    sellers = sku_item.get("sellers") or []
    if not sellers or "commertialOffer" not in sellers[0]:
        return None

    offer = sellers[0]["commertialOffer"]
    cantidad_disponible = int(offer.get("AvailableQuantity", 0) or 0)

    if cantidad_disponible == 0:
        return {"Precio_Final": "Sin Stock", "Precio_Lista": "Sin Stock", "Descuento": 0, "Stock": "Sin Stock"}

    precio_final = int(float(offer.get("Price", 0) or 0))
    precio_lista = int(float(offer.get("ListPrice", 0) or 0))

    descuento = 0
    if precio_lista > precio_final > 0:
        descuento = round(((precio_lista - precio_final) / precio_lista) * 100, 2)
        # El campo ListPrice esta mal mantenido en varios VTEX de super-
        # mercados (ej. $252.066 de "lista" para un producto de $3.050):
        # un descuento real casi nunca supera ~85-90%. Si lo supera, es
        # casi seguro que ListPrice es basura, no una oferta real; en ese
        # caso descartamos el precio de lista en vez de reportar un
        # descuento inventado.
        if descuento > 90:
            precio_lista = precio_final
            descuento = 0

    return {"Precio_Final": precio_final, "Precio_Lista": precio_lista, "Descuento": descuento, "Stock": "Con Stock"}


def vtex_armar_producto(nombre_retailer, res_item, sku_item, ean_api, k, metodo):
    oferta = vtex_extraer_oferta(sku_item)
    if not oferta:
        print(f"     [!] Sin oferta/vendedor disponible para {res_item.get('productName')}")
        return None

    return {
        "Grupo": k.get("marca") or "Molinos",
        "Retailer": nombre_retailer,
        "Fecha": datetime.now().strftime("%Y-%m-%d"),
        "EAN": ean_api if ean_api else "N/A",
        "Nombre": res_item.get("productName", ""),
        "Precio_Lista": oferta["Precio_Lista"],
        "Precio_Final": oferta["Precio_Final"],
        "Porcentaje_Oferta": oferta["Descuento"],
        "Stock": oferta["Stock"],
        "Link": res_item.get("link", ""),
        "EAN_Original": k["ean"],
        "Nombre_Original": k["nombre_raw"],
        "Metodo_Match": metodo,
    }


def vtex_resolver_desde_url(session, base_url, url):
    api_url = f"{base_url}/api/catalog_system/pub/products/search/{slug_producto_vtex(url)}/p"
    return vtex_buscar_json(session, api_url)


def vtex_buscar_producto(session, base_url, nombre_retailer, k, urls_prioridad):
    """Prueba, en orden, URL de prioridad -> variantes de EAN -> SKU ID ->
    escalera de variantes de nombre. Se queda con la primera que de un
    resultado valido (validado por EAN cuando lo tenemos)."""
    estrategias = []

    key_fb = f"{k['ean']}_{k['nombre_raw']}"
    if key_fb in urls_prioridad:
        estrategias.append(("URL Prioridad", lambda: vtex_resolver_desde_url(session, base_url, urls_prioridad[key_fb])))

    for ean_variante in variantes_ean(k["ean"]):
        estrategias.append(
            ("EAN", lambda e=ean_variante: vtex_buscar_json(session, f"{base_url}/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{e}"))
        )
    if k["sku"]:
        estrategias.append(
            ("SKU ID", lambda: vtex_buscar_json(session, f"{base_url}/api/catalog_system/pub/products/search?fq=skuId:{k['sku']}"))
        )
    if k["nombre_limpio"]:
        for i, variante in enumerate(variantes_busqueda_nombre(k["nombre_limpio"])):
            etiqueta = "Nombre" if i == 0 else f"Nombre (variante {i + 1})"
            # "?ft=" (busqueda de texto libre de bajo nivel) funciona en las
            # 5 cadenas nuevas; la ruta "/search/{termino}" (sin ft=) les
            # devuelve 0 resultados aunque el status sea 200/206.
            url_busqueda = f"{base_url}/api/catalog_system/pub/products/search?ft={urllib.parse.quote(variante)}"
            estrategias.append(
                (etiqueta, lambda u=url_busqueda, n=k["nombre_limpio"]: vtex_buscar_por_nombre(session, u, n))
            )

    for metodo, estrategia in estrategias:
        res_item = estrategia()
        if not res_item:
            continue

        sku_item, ean_api = vtex_elegir_sku(res_item, k["ean"])
        if k["ean"] and not sku_item:
            print(f"     [!] Descartado ({metodo}): EAN esperado {k['ean']} no está en las variantes de {res_item.get('productName')}.")
            continue

        producto = vtex_armar_producto(nombre_retailer, res_item, sku_item, ean_api, k, metodo)
        if producto:
            print(f"     [OK] Encontrado ({metodo}): {producto['Nombre']}")
            return producto

    return None


def ejecutar_scraper_vtex(nombre_retailer, filtro_fallback, base_url, pausa=0.3):
    """Corre el pipeline completo de 2 fases (busqueda automatica + URLs de
    fallback manual) para un retailer VTEX y guarda el resultado. Esta es
    toda la logica que necesita cada scraper de supermercado: el archivo
    scraping_xxx.py de cada cadena es solo un wrapper de este motor con su
    propia URL base."""
    print(f"--- INICIANDO SCRAPER {nombre_retailer.upper()} (VTEX) ---")

    session = crear_sesion()
    urls_prioridad = cargar_urls_prioridad(filtro_fallback)
    productos_seed = cargar_productos()

    print("\n--- FASE 1: BÚSQUEDA DE PRODUCTOS ---")
    print(f"Se procesarán {len(productos_seed)} productos.")

    productos_extraidos = []
    for k in productos_seed:
        print(f"  -> Procesando: {k['nombre_raw'][:50]}...")
        producto = vtex_buscar_producto(session, base_url, nombre_retailer, k, urls_prioridad)
        time.sleep(pausa)
        if producto:
            productos_extraidos.append(producto)
        else:
            print(f"     [!] No disponible en {nombre_retailer}.")

    print("\n--- FASE 2: PROCESANDO URLs DE FALLBACK MANUAL ---")
    eans_ya_encontrados = {p["EAN"] for p in productos_extraidos}
    pendientes = cargar_fallback_pendientes(filtro_fallback, eans_ya_encontrados)
    print(f"Se encontraron {len(pendientes)} URLs de Fallback pendientes para {nombre_retailer}.")

    for item in pendientes:
        print(f"  -> Procesando Fallback EAN {item['ean']}: {item['url']}")
        res_item = vtex_resolver_desde_url(session, base_url, item["url"])
        time.sleep(pausa)
        if not res_item:
            print("     [!] No se pudo obtener datos del fallback")
            continue

        sku_item, ean_api = vtex_elegir_sku(res_item, "")
        k_fallback = {"ean": item["ean"], "nombre_raw": item["nombre_original"], "marca": ""}
        producto = vtex_armar_producto(nombre_retailer, res_item, sku_item, ean_api or item["ean"], k_fallback, "URL Fallback")
        if producto:
            productos_extraidos.append(producto)
            print(f"     [OK] Encontrado vía Fallback: {producto['Nombre']}")

    guardar_resultados(productos_extraidos, f"{nombre_retailer}_VTEX")
