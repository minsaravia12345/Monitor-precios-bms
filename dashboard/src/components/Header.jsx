import { IconSun, IconMoon, IconTarget, IconClock } from './Icons';

export default function Header({ ultimaActualizacion, theme, onToggleTheme }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <span className="brand-mark">
            <IconTarget width={20} height={20} />
          </span>
          <div className="brand-text">
            <h1>
              Molinos S.A. <span className="brand-text-light">Pricing Intelligence</span>
            </h1>
            <p>Solución desarrollada para Molinos Río de la Plata · Equipo Pricing &amp; Revenue</p>
          </div>
        </div>

        <div className="topbar-right">
          <span className="internal-pill">Uso interno</span>
          {ultimaActualizacion && (
            <span className="sync-info">
              <IconClock width={15} height={15} />
              <span className="sync-text">Actualizado {ultimaActualizacion}</span>
            </span>
          )}
          <button
            type="button"
            className="icon-btn"
            onClick={onToggleTheme}
            aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
            title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
          >
            {theme === 'dark' ? <IconSun /> : <IconMoon />}
          </button>
        </div>
      </div>
    </header>
  );
}
