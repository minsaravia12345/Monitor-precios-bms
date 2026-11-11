import { IconLayers, IconTarget, IconStore } from './Icons';

export default function StatsOverview({ total, marcas, porFarmacia }) {
  return (
    <div className="stats-grid">
      <div className="stat-tile" style={{ '--tile-color': '#60a5fa' }}>
        <span className="stat-icon">
          <IconLayers width={18} height={18} />
        </span>
        <div className="stat-body">
          <span className="stat-value">{total}</span>
          <span className="stat-label">Productos monitoreados</span>
        </div>
      </div>

      <div className="stat-tile" style={{ '--tile-color': '#34d399' }}>
        <span className="stat-icon">
          <IconTarget width={18} height={18} />
        </span>
        <div className="stat-body">
          <span className="stat-value">{marcas}</span>
          <span className="stat-label">Marcas Molinos monitoreadas</span>
        </div>
      </div>

      {porFarmacia.map((f) => (
        <div className="stat-tile" key={f.key} style={{ '--tile-color': f.color }}>
          <span className="stat-icon">
            <IconStore width={18} height={18} />
          </span>
          <div className="stat-body">
            <span className="stat-value">{f.count}</span>
            <span className="stat-label">Gana {f.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
