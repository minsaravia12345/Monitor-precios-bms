import { IconSearch, IconX } from './Icons';

export default function Toolbar({
  tabActivo,
  setTabActivo,
  search,
  setSearch,
  grupos,
  filtroGrupo,
  setFiltroGrupo,
  farmaciasVisibles,
  filtroGanador,
  setFiltroGanador,
  sortBy,
  setSortBy,
}) {
  const mostrarGrupoSelect = grupos.length > 2;

  return (
    <div className="toolbar">
      <div className="tabs" role="tablist" aria-label="Vista de productos">
        <button
          type="button"
          role="tab"
          aria-selected={tabActivo === 'explorar'}
          className={`tab-btn ${tabActivo === 'explorar' ? 'active' : ''}`}
          onClick={() => setTabActivo('explorar')}
        >
          Catálogo
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tabActivo === 'killers'}
          className={`tab-btn tab-btn-alert ${tabActivo === 'killers' ? 'active' : ''}`}
          onClick={() => setTabActivo('killers')}
          aria-describedby="oportunidades-hint"
        >
          Oportunidades
        </button>
        <span id="oportunidades-hint" className="visually-hidden">
          Productos con Market Opportunity Score (MOS) mayor o igual a 65
        </span>
      </div>

      <div className="search-box">
        <IconSearch width={16} height={16} />
        <input
          type="text"
          className="search-input"
          placeholder="Buscar por nombre o EAN..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Buscar producto"
        />
        {search && (
          <button
            type="button"
            className="search-clear"
            onClick={() => setSearch('')}
            aria-label="Limpiar búsqueda"
          >
            <IconX width={14} height={14} />
          </button>
        )}
      </div>

      {mostrarGrupoSelect && (
        <select
          className="select-field"
          value={filtroGrupo}
          onChange={(e) => setFiltroGrupo(e.target.value)}
          aria-label="Filtrar por grupo"
        >
          {grupos.map((g) => (
            <option key={g} value={g}>
              {g === 'Todos' ? 'Todos los grupos' : g}
            </option>
          ))}
        </select>
      )}

      <select
        className="select-field"
        value={filtroGanador}
        onChange={(e) => setFiltroGanador(e.target.value)}
        aria-label="Filtrar por ganador"
      >
        <option value="Todos">Cualquier ganador de precio</option>
        {farmaciasVisibles.map((f) => (
          <option key={f.key} value={f.label}>
            Gana {f.label}
          </option>
        ))}
        <option value="Empate">Empate</option>
      </select>

      <div className="toolbar-spacer" />

      <select
        className="select-field"
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value)}
        aria-label="Ordenar productos"
      >
        <option value="mos_desc">Mayor oportunidad (MOS)</option>
        <option value="price_index_desc">Price Index más alto</option>
        <option value="promo_desc">Mayor presión promocional</option>
        <option value="ahorro_desc">Mayor brecha de mercado</option>
        <option value="precio_asc">Menor precio</option>
        <option value="nombre_asc">Nombre A-Z</option>
      </select>
    </div>
  );
}
