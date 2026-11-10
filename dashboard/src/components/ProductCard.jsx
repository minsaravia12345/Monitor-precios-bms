import { esNumeroValido, parseNumero, formatearPrecio } from '../utils/format';
import { tierMOS } from '../utils/metrics';

const FARMACITY_KEY = 'Farmacity';

function PharmacyRow({ prod, farmacia }) {
  const pData = prod.Precios?.[farmacia.key];
  const isWinner = prod.Ganador && prod.Ganador.includes(farmacia.label);
  const esFarmacity = farmacia.key === FARMACITY_KEY;

  if (!pData) {
    return (
      <div className={`pharmacy-price unavailable ${esFarmacity ? 'is-self' : ''}`}>
        <span className="pharmacy-name">
          <span className="store-dot" style={{ background: farmacia.color }} />
          {farmacia.label}
          {esFarmacity && <span className="self-tag">Vos</span>}
        </span>
        <span className="no-avail">No disponible</span>
      </div>
    );
  }

  const sinStock = pData.Stock && pData.Stock !== 'Con Stock';

  if (sinStock) {
    return (
      <div className={`pharmacy-price unavailable ${esFarmacity ? 'is-self' : ''}`}>
        <span className="pharmacy-name">
          <span className="store-dot" style={{ background: farmacia.color }} />
          {farmacia.label}
          {esFarmacity && <span className="self-tag">Vos</span>}
        </span>
        <span className="no-avail">Sin stock</span>
      </div>
    );
  }

  const esFinalNum = esNumeroValido(pData.Precio_Final);
  const esListaNum = esNumeroValido(pData.Precio_Lista);
  const precioLista = parseNumero(pData.Precio_Lista);
  const precioFinal = parseNumero(pData.Precio_Final);
  const hayTachado = esListaNum && esFinalNum && precioLista > precioFinal;

  return (
    <a
      href={pData.Link}
      target="_blank"
      rel="noreferrer"
      className={`pharmacy-price ${isWinner ? 'winner' : ''} ${esFarmacity ? 'is-self' : ''}`}
    >
      <span className="pharmacy-name">
        <span className="store-dot" style={{ background: farmacia.color }} />
        {farmacia.label}
        {esFarmacity && <span className="self-tag">Vos</span>}
      </span>
      <div className="price-details">
        <span className={`actual-price ${esFinalNum ? 'currency' : ''} ${isWinner ? 'winner-text' : ''}`}>
          {formatearPrecio(pData.Precio_Final)}
          {esFinalNum && pData.Descuento > 0 && (
            <span className="discount-badge">-{pData.Descuento}%</span>
          )}
        </span>
        {hayTachado && <span className="list-price currency">{formatearPrecio(pData.Precio_Lista)}</span>}
      </div>
    </a>
  );
}

function etiquetaGanador(ganador) {
  if (ganador === 'Empate') return 'Empate de mercado';
  if (!ganador || ganador === 'Sin precio') return 'Sin precio en el mercado';
  return `Gana ${ganador}`;
}

export default function ProductCard({ producto, farmacias, delay }) {
  const esEmpate = producto.Ganador === 'Empate';
  const { priceIndex, promoPressure, mos } = producto.metricas;
  const mTier = tierMOS(mos);

  return (
    <div
      className={`product-card tone-${mTier.tone}`}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="card-head">
        <span className={`group-badge ${producto.Es_Killer ? 'killer' : ''}`}>
          {producto.Es_Killer ? '🎯 Producto estratégico' : producto.Grupo}
        </span>
        {producto.EAN && producto.EAN !== 'N/A' && <span className="ean-tag">EAN {producto.EAN}</span>}
      </div>

      <h3 className="product-name">{producto.Nombre}</h3>

      <div className="metric-chips">
        <span className="metric-chip" title="Price Index: precio de Farmacity vs. promedio competidor (100 = paridad)">
          <span className="metric-chip-label">Price Index</span>
          <span className="metric-chip-value">{priceIndex === null ? '—' : priceIndex}</span>
        </span>
        <span className="metric-chip" title="Promo Pressure: intensidad promocional de la competencia (0-100)">
          <span className="metric-chip-label">Promo</span>
          <span className="metric-chip-value">{promoPressure}</span>
        </span>
        <span className={`metric-chip metric-chip-mos tone-${mTier.tone}`} title="Market Opportunity Score (0-100)">
          <span className="metric-chip-label">MOS</span>
          <span className="metric-chip-value">{mos}</span>
        </span>
      </div>

      <div className="prices-container">
        {farmacias.map((f) => (
          <PharmacyRow prod={producto} farmacia={f} key={f.key} />
        ))}
      </div>

      <div className="card-footer">
        <span className={`winner-badge ${esEmpate || !producto.Ganador || producto.Ganador === 'Sin precio' ? 'empate' : ''}`}>
          {etiquetaGanador(producto.Ganador)}
        </span>
        {producto.Diferencia_Porcentual > 0 && (
          <span className="difference">Brecha de mercado {producto.Diferencia_Porcentual}%</span>
        )}
      </div>

      <p className={`accion-sugerida tone-${mTier.tone}`}>
        <span className="accion-dot" /> {mTier.accion}
      </p>
    </div>
  );
}
