import { parseNumero } from './format';

const FARMACITY_KEY = 'Farmacity';

function preciosEntries(producto) {
  return Object.entries(producto.Precios || {});
}

function precioValido(data) {
  if (!data) return null;
  if (data.Stock && data.Stock !== 'Con Stock') return null;
  return parseNumero(data.Precio_Final);
}

/**
 * Price Index: precio de Farmacity respecto al promedio de la competencia.
 * 100 = paridad, >100 = Farmacity más caro, <100 = Farmacity más barato.
 * null = Farmacity no tiene oferta activa o no hay competencia con precio para comparar.
 */
export function calcularPriceIndex(producto) {
  const fPrecio = precioValido(producto.Precios?.[FARMACITY_KEY]);
  if (fPrecio === null) return null;

  const competidores = preciosEntries(producto)
    .filter(([key]) => key !== FARMACITY_KEY)
    .map(([, data]) => precioValido(data))
    .filter((n) => n !== null);

  if (competidores.length === 0) return null;

  const promedio = competidores.reduce((a, b) => a + b, 0) / competidores.length;
  if (!promedio) return null;

  return Math.round((fPrecio / promedio) * 100);
}

/**
 * Promo Pressure: qué tan agresiva es la competencia con descuentos frente a Farmacity.
 * Escala 0-100. 50 = equilibrio, >50 = la competencia descuenta más fuerte que Farmacity.
 */
export function calcularPromoPressure(producto) {
  const fData = producto.Precios?.[FARMACITY_KEY];
  const fDescuento = fData && fData.Stock !== 'Sin Stock' ? Number(fData.Descuento) || 0 : 0;

  const descuentosCompetencia = preciosEntries(producto)
    .filter(([key]) => key !== FARMACITY_KEY)
    .map(([, data]) => (data.Stock !== 'Sin Stock' ? Number(data.Descuento) || 0 : null))
    .filter((n) => n !== null);

  if (descuentosCompetencia.length === 0) return 50;

  const maxCompetencia = Math.max(...descuentosCompetencia);
  const presion = 50 + (maxCompetencia - fDescuento);
  return Math.max(0, Math.min(100, Math.round(presion)));
}

/**
 * Visibility Index: cobertura real del producto por parte de Farmacity,
 * relativa a la cantidad de canales donde el producto está disponible.
 */
export function calcularVisibilityIndex(producto, totalFarmacias) {
  const fTienePrecio = precioValido(producto.Precios?.[FARMACITY_KEY]) !== null;
  if (!totalFarmacias) return fTienePrecio ? 100 : 0;
  const disponibleEn = Number(producto.Disponible_En) || 0;
  const base = Math.round((disponibleEn / totalFarmacias) * 100);
  return fTienePrecio ? base : Math.round(base * 0.4);
}

/**
 * Market Opportunity Score (MOS): prioriza qué productos conviene accionar primero.
 * Combina brecha de precio, presión promocional y visibilidad. Escala 0-100.
 */
export function calcularMOS({ priceIndex, promoPressure, visibilityIndex }) {
  const gapScore = priceIndex === null ? 82 : Math.max(0, Math.min(100, priceIndex - 50));
  const visGap = 100 - visibilityIndex;
  const score = 0.45 * gapScore + 0.35 * promoPressure + 0.2 * visGap;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function calcularMetricas(producto, totalFarmacias) {
  const priceIndex = calcularPriceIndex(producto);
  const promoPressure = calcularPromoPressure(producto);
  const visibilityIndex = calcularVisibilityIndex(producto, totalFarmacias);
  const mos = calcularMOS({ priceIndex, promoPressure, visibilityIndex });
  return { priceIndex, promoPressure, visibilityIndex, mos };
}

export function tierPriceIndex(valor) {
  if (valor === null) return { label: 'Sin oferta activa', tone: 'critical' };
  if (valor <= 97) return { label: 'Más barato que el mercado', tone: 'good' };
  if (valor <= 103) return { label: 'En paridad con el mercado', tone: 'neutral' };
  return { label: 'Por encima del mercado', tone: 'critical' };
}

export function tierPromoPressure(valor) {
  if (valor < 40) return { label: 'Presión baja', tone: 'good' };
  if (valor <= 60) return { label: 'Presión moderada', tone: 'neutral' };
  return { label: 'Presión alta de la competencia', tone: 'critical' };
}

export function tierVisibility(valor) {
  if (valor >= 90) return { label: 'Cobertura alta', tone: 'good' };
  if (valor >= 70) return { label: 'Cobertura media', tone: 'neutral' };
  return { label: 'Cobertura baja', tone: 'critical' };
}

/**
 * Bandas de MOS tal como las define la tesis: 80-100 empujar fuerte,
 * 60-80 empujar selectivo, 40-60 mantener, <40 no empujar.
 */
export function tierMOS(valor) {
  if (valor >= 80) return { label: 'Empujar fuerte', tone: 'critical', accion: 'Empujar fuerte: prioridad máxima' };
  if (valor >= 60) return { label: 'Empujar selectivo', tone: 'elevated', accion: 'Empujar selectivo en el canal con mayor brecha' };
  if (valor >= 40) return { label: 'Mantener', tone: 'neutral', accion: 'Mantener posición' };
  return { label: 'No empujar', tone: 'good', accion: 'No empujar: posición estable' };
}

/**
 * Convierte el Price Index (base 100) al formato ratio que usa la tesis,
 * ej. 1.08 = "8% más caro que el entorno competitivo".
 */
export function formatPriceIndexRatio(priceIndex) {
  if (priceIndex === null) return { ratio: '—', diffLabel: 's/d' };
  const ratio = (priceIndex / 100).toFixed(2);
  const diff = Math.round(priceIndex - 100);
  const sign = diff > 0 ? '+' : '';
  return { ratio, diffLabel: `${sign}${diff}%` };
}

/**
 * Diagnóstico cruzado Price Index + Promo Pressure, siguiendo las reglas de la tesis:
 * "Promo Pressure alta + Price Index alto = riesgo de pérdida de ventas";
 * "Promo Pressure baja + Price Index alto = se puede sostener precio".
 */
export function diagnosticoCombinado(priceIndex, promoPressure) {
  const promoAlta = promoPressure > 60;
  const promoBaja = promoPressure < 40;
  const priceAlto = priceIndex !== null && priceIndex > 103;
  const priceBajo = priceIndex !== null && priceIndex < 97;

  if (priceIndex === null) {
    return promoAlta
      ? { texto: 'Sin oferta propia y la competencia en plena ofensiva promocional: posible hueco de mercado.', tone: 'critical' }
      : { texto: 'Sin oferta propia activa para este producto.', tone: 'neutral' };
  }
  if (priceAlto && promoAlta) {
    return { texto: 'Riesgo de pérdida de ventas: precio por encima del mercado y competencia promocionando fuerte.', tone: 'critical' };
  }
  if (priceAlto && promoBaja) {
    return { texto: 'Se puede sostener el precio: poca presión promocional de la competencia.', tone: 'neutral' };
  }
  if (priceAlto) {
    return { texto: 'Precio por encima del mercado con presión promocional moderada: vigilar.', tone: 'elevated' };
  }
  if (priceBajo && promoAlta) {
    return { texto: 'Oportunidad de ganar volumen: precio competitivo frente a una ofensiva promocional.', tone: 'good' };
  }
  if (priceBajo) {
    return { texto: 'Posición cómoda: precio por debajo del mercado.', tone: 'good' };
  }
  return promoAlta
    ? { texto: 'Precio en paridad, pero la competencia promociona fuerte: vigilar de cerca.', tone: 'elevated' }
    : { texto: 'Precio en paridad y presión promocional bajo control.', tone: 'good' };
}
