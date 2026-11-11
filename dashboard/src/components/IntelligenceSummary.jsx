import { tierPriceIndex, tierPromoPressure, tierVisibility, tierMOS } from '../utils/metrics';

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

  return (
    <section className="intel-grid" aria-label="Indicadores de inteligencia competitiva">
      <div className={`intel-card tone-${pTier.tone}`}>
        <div className="intel-head">
          <span className="intel-label">Price Index</span>
          <span className="intel-pill">entre canales</span>
        </div>
        <div className="intel-value">{priceIndex === null ? '—' : `${(priceIndex / 100).toFixed(2)}x`}</div>
        <Gauge value={priceIndex === null ? 0 : priceIndex} max={160} tone={pTier.tone} />
        <p className="intel-caption">{pTier.label}</p>
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
          <span className="intel-label">Visibility Index</span>
          <span className="intel-pill">cobertura</span>
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
          {mTier.label} · <strong>{oportunidadesCriticas}</strong> producto{oportunidadesCriticas !== 1 ? 's' : ''} para accionar
        </p>
      </div>
    </section>
  );
}
