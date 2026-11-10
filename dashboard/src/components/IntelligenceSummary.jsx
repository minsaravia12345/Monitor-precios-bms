import { IconInfo } from './Icons';
import { tierPriceIndex, tierPromoPressure, tierVisibility, tierMOS, formatPriceIndexRatio } from '../utils/metrics';

function Gauge({ value, max = 100, tone }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`gauge-track tone-${tone}`}>
      <div className="gauge-fill" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function IntelligenceSummary({ priceIndex, promoPressure, visibilityIndex, mos, oportunidadesCriticas }) {
  const pTier = tierPriceIndex(priceIndex);
  const prTier = tierPromoPressure(promoPressure);
  const vTier = tierVisibility(visibilityIndex);
  const mTier = tierMOS(mos);
  const { ratio, diffLabel } = formatPriceIndexRatio(priceIndex);

  return (
    <section className="intel-grid" aria-label="Indicadores de inteligencia competitiva">
      <div className={`intel-card tone-${pTier.tone}`}>
        <div className="intel-head">
          <span className="intel-label">Price Index</span>
          <span className="intel-pill">vs. mercado</span>
        </div>
        <div className="intel-value">{priceIndex === null ? '—' : `${ratio}x`}</div>
        <Gauge value={priceIndex === null ? 0 : priceIndex} max={160} tone={pTier.tone} />
        <p className="intel-caption">
          {pTier.label} · {diffLabel} vs. mercado
        </p>
      </div>

      <div className={`intel-card tone-${prTier.tone}`}>
        <div className="intel-head">
          <span className="intel-label">Promo Pressure</span>
          <span className="intel-pill">0–100</span>
        </div>
        <div className="intel-value">{promoPressure}</div>
        <Gauge value={promoPressure} tone={prTier.tone} />
        <p className="intel-caption">{prTier.label}</p>
      </div>

      <div className={`intel-card tone-${vTier.tone}`}>
        <div className="intel-head">
          <span className="intel-label">
            Visibility Index
            <IconInfo
              width={13}
              height={13}
              className="info-icon"
              title="Proxy simplificado para este MVP: aproxima la cobertura de catálogo frente a la competencia. La versión completa de SCOUT mide exposición real en el recorrido de compra (posición en búsqueda, banners, SKUs visibles)."
            />
          </span>
          <span className="intel-pill">proxy de cobertura</span>
        </div>
        <div className="intel-value">{visibilityIndex}%</div>
        <Gauge value={visibilityIndex} tone={vTier.tone} />
        <p className="intel-caption">{vTier.label}</p>
      </div>

      <div className={`intel-card tone-${mTier.tone} intel-card-highlight`}>
        <div className="intel-head">
          <span className="intel-label">Market Opportunity Score</span>
          <span className="intel-pill">MOS</span>
        </div>
        <div className="intel-value">{mos}</div>
        <Gauge value={mos} tone={mTier.tone} />
        <p className="intel-caption">
          {mTier.label} · <strong>{oportunidadesCriticas}</strong> producto{oportunidadesCriticas !== 1 ? 's' : ''} con MOS ≥ 80
        </p>
      </div>
    </section>
  );
}
