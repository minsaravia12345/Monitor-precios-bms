import { parseNumero } from './format';

function preciosEntries(producto) {
  return Object.entries(producto.Precios || {});
}

function precioValido(data) {
  if (!data) return null;
  if (data.Stock && data.Stock !== 'Con Stock') return null;
  return parseNumero(data.Precio_Final);
}

/**
 * Price Index: dispersión de precio entre los retailers que venden el
 * producto, como ratio (precio más caro / precio más barato) * 100.
 * 100 = todos cobran lo mismo. Cuanto más alto, mayor diferencia entre el
 * canal más caro y el más barato: riesgo de conflicto de canal para la marca.
 * null = no hay al menos 2 retailers con precio válido para comparar.
 */
export function calcularPriceIndex(producto) {
  const precios = preciosEntries(producto)
    .map(([, data]) => precioValido(data))
    .filter((n) => n !== null && n > 0);

  if (precios.length < 2) return null;

  const min = Math.min(...precios);
  const max = Math.max(...precios);
  if (!min) return null;

  return Math.round((max / min) * 100);
}

/**
 * Promo Pressure: qué fracción de los retailers que tienen el producto en
 * stock lo están vendiendo hoy con descuento activo o con una promoción
 * condicionada (tarjeta del canal, 2x1, etc.). Escala 0-100.
 *
 * En los supermercados argentinos la promo real casi nunca baja el precio
 * de góndola (Price/ListPrice): es un descuento condicionado que VTEX
 * expone aparte (ej. "Tarjeta Carrefour 15%"), guardado acá en
 * `Promocion`. Contar solo Descuento > 0 subestima drásticamente la
 * presión promocional real del canal.
 */
export function calcularPromoPressure(producto) {
  const conStock = preciosEntries(producto).filter(([, data]) => data.Stock !== 'Sin Stock');
  if (conStock.length === 0) return 0;

  const conPromo = conStock.filter(
    ([, data]) => Number(data.Descuento) > 0 || Boolean(data.Promocion)
  ).length;
  return Math.round((conPromo / conStock.length) * 100);
}

/**
 * Visibility Index: en qué fracción de los retailers monitoreados está
 * efectivamente disponible el producto (con precio válido).
 */
export function calcularVisibilityIndex(producto, totalRetailers) {
  if (!totalRetailers) return 0;
  const disponibleEn = Number(producto.Disponible_En) || 0;
  return Math.round((disponibleEn / totalRetailers) * 100);
}

/**
 * Market Opportunity Score (MOS): prioriza qué productos conviene revisar
 * primero por riesgo de conflicto de canal, combinando dispersión de
 * precio, presión promocional y cobertura. Escala 0-100.
 */
export function calcularMOS({ priceIndex, promoPressure, visibilityIndex }) {
  const gapScore = priceIndex === null ? 20 : Math.max(0, Math.min(100, (priceIndex - 100) * 2));
  const visGap = 100 - visibilityIndex;
  const score = 0.5 * gapScore + 0.3 * promoPressure + 0.2 * visGap;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function calcularMetricas(producto, totalRetailers) {
  const priceIndex = calcularPriceIndex(producto);
  const promoPressure = calcularPromoPressure(producto);
  const visibilityIndex = calcularVisibilityIndex(producto, totalRetailers);
  const mos = calcularMOS({ priceIndex, promoPressure, visibilityIndex });
  return { priceIndex, promoPressure, visibilityIndex, mos };
}

export function tierPriceIndex(valor) {
  if (valor === null) return { label: 'Sin datos suficientes', tone: 'neutral' };
  if (valor <= 105) return { label: 'Precio consistente entre canales', tone: 'good' };
  if (valor <= 120) return { label: 'Dispersión moderada entre canales', tone: 'neutral' };
  return { label: 'Alta dispersión: riesgo de conflicto de canal', tone: 'critical' };
}

export function tierPromoPressure(valor) {
  if (valor < 30) return { label: 'Baja actividad promocional', tone: 'good' };
  if (valor <= 60) return { label: 'Actividad promocional moderada', tone: 'neutral' };
  return { label: 'Alta actividad promocional en el canal', tone: 'critical' };
}

export function tierVisibility(valor) {
  if (valor >= 80) return { label: 'Presente en casi todos los canales', tone: 'good' };
  if (valor >= 50) return { label: 'Presencia parcial en el canal', tone: 'neutral' };
  return { label: 'Baja presencia en el canal', tone: 'critical' };
}

export function tierMOS(valor) {
  if (valor >= 65) return { label: 'Alto riesgo de canal', tone: 'critical', accion: 'Revisar pricing con el canal ahora' };
  if (valor >= 35) return { label: 'Riesgo moderado', tone: 'neutral', accion: 'Monitorear de cerca' };
  return { label: 'Bajo riesgo', tone: 'good', accion: 'Consistencia saludable' };
}
