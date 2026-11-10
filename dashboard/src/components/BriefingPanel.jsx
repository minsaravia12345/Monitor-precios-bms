import { IconFlag, IconArrowRight } from './Icons';
import { tierMOS } from '../utils/metrics';

export default function BriefingPanel({ counts, topOportunidades, onSeleccionarProducto }) {
  return (
    <section className="briefing-panel" aria-label="Resumen de prioridades">
      <div className="briefing-head">
        <span className="briefing-icon">
          <IconFlag width={18} height={18} />
        </span>
        <div>
          <h3>Antes de arrancar: tus prioridades de hoy</h3>
          <p>
            <strong>{counts.empujarFuerte}</strong> producto{counts.empujarFuerte !== 1 ? 's' : ''} para empujar
            fuerte, <strong>{counts.empujarSelectivo}</strong> para empuje selectivo y{' '}
            <strong>{counts.riesgoPerdida}</strong> con riesgo de pérdida de ventas por presión promocional.
          </p>
        </div>
      </div>

      <ol className="briefing-list">
        {topOportunidades.map((p, idx) => {
          const tier = tierMOS(p.metricas.mos);
          return (
            <li key={p.Id} className="briefing-item">
              <span className="briefing-rank">{idx + 1}</span>
              <div className="briefing-info">
                <span className="briefing-name">{p.Nombre}</span>
                <span className="briefing-diag">{p.diagnostico.texto}</span>
              </div>
              <span className={`briefing-mos tone-${tier.tone}`}>MOS {p.metricas.mos}</span>
              <button
                type="button"
                className="briefing-cta"
                onClick={() => onSeleccionarProducto(p)}
                aria-label={`Ver ${p.Nombre} en el catálogo`}
              >
                Ver <IconArrowRight width={14} height={14} />
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
