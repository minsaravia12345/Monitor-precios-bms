import { esNumeroValido, parseNumero, formatearPrecio } from '../utils/format';

function PharmacyRow({ prod, farmacia }) {
  const pData = prod.Precios?.[farmacia.key];
  const isWinner = prod.Ganador && prod.Ganador.includes(farmacia.label);

  if (!pData) {
    return (
      <div className="pharmacy-price unavailable">
        <span className="pharmacy-name">
          <span className="store-dot" style={{ background: farmacia.color }} />
          {farmacia.label}
        </span>
        <span className="no-avail">No disponible</span>
      </div>
    );
  }

  const sinStock = pData.Stock && pData.Stock !== 'Con Stock';

  if (sinStock) {
    return (
      <div className="pharmacy-price unavailable">
        <span className="pharmacy-name">
          <span className="store-dot" style={{ background: farmacia.color }} />
          {farmacia.label}
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
      className={`pharmacy-price ${isWinner ? 'winner' : ''}`}
    >
      <span className="pharmacy-name">
        <span className="store-dot" style={{ background: farmacia.color }} />
        {farmacia.label}
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

export default function ProductCard({ producto, farmacias, delay }) {
  const esEmpate = producto.Ganador === 'Empate';

  return (
    <div
      className={`product-card ${producto.Es_Killer ? 'killer-style' : ''}`}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="card-head">
        <span className={`group-badge ${producto.Es_Killer ? 'killer' : ''}`}>
          {producto.Es_Killer ? '🎯 Producto estratégico' : producto.Grupo}
        </span>
        {producto.EAN && producto.EAN !== 'N/A' && <span className="ean-tag">EAN {producto.EAN}</span>}
      </div>

      <h3 className="product-name">{producto.Nombre}</h3>

      <div className="prices-container">
        {farmacias.map((f) => (
          <PharmacyRow prod={producto} farmacia={f} key={f.key} />
        ))}
      </div>

      <div className="card-footer">
        <span className={`winner-badge ${esEmpate ? 'empate' : ''}`}>
          {esEmpate ? 'Empate' : `Gana ${producto.Ganador}`}
        </span>
        {producto.Diferencia_Porcentual > 0 && (
          <span className="difference">Ahorro máx. {producto.Diferencia_Porcentual}%</span>
        )}
      </div>
    </div>
  );
}
