export default function AdvancedFilters({
  filtroStock,
  setFiltroStock,
  filtroBrechaMin,
  setFiltroBrechaMin,
  filtroDescuento,
  setFiltroDescuento,
  soloPerdiendo,
  setSoloPerdiendo,
  filtroPrecioRango,
  setFiltroPrecioRango,
}) {
  return (
    <div className="advanced-filters" role="group" aria-label="Filtros avanzados para el equipo comercial">
      <div className="advanced-filter-field">
        <label htmlFor="filtro-precio">Rango de precio</label>
        <select
          id="filtro-precio"
          className="select-field"
          value={filtroPrecioRango}
          onChange={(e) => setFiltroPrecioRango(e.target.value)}
        >
          <option value="Todos">Cualquier precio</option>
          <option value="bajo">Menos de $15.000</option>
          <option value="medio">$15.000 a $50.000</option>
          <option value="alto">Más de $50.000</option>
        </select>
      </div>

      <div className="advanced-filter-field">
        <label htmlFor="filtro-stock">Stock en Farmacity</label>
        <select
          id="filtro-stock"
          className="select-field"
          value={filtroStock}
          onChange={(e) => setFiltroStock(e.target.value)}
        >
          <option value="Todos">Cualquier estado</option>
          <option value="Con stock">Con stock</option>
          <option value="Sin stock">Sin stock</option>
          <option value="No comercializado">No se vende en Farmacity</option>
        </select>
      </div>

      <div className="advanced-filter-field">
        <label htmlFor="filtro-brecha">Brecha de precio mínima</label>
        <select
          id="filtro-brecha"
          className="select-field"
          value={filtroBrechaMin}
          onChange={(e) => setFiltroBrechaMin(Number(e.target.value))}
        >
          <option value={0}>Cualquier brecha</option>
          <option value={10}>10% o más</option>
          <option value={25}>25% o más</option>
          <option value={40}>40% o más</option>
        </select>
      </div>

      <div className="advanced-filter-field">
        <label htmlFor="filtro-descuento">Descuento en Farmacity</label>
        <select
          id="filtro-descuento"
          className="select-field"
          value={filtroDescuento}
          onChange={(e) => setFiltroDescuento(e.target.value)}
        >
          <option value="Todos">Cualquiera</option>
          <option value="Con descuento">Con descuento activo</option>
          <option value="Sin descuento">Sin descuento</option>
        </select>
      </div>

      <label className="toggle-chip">
        <input
          type="checkbox"
          checked={soloPerdiendo}
          onChange={(e) => setSoloPerdiendo(e.target.checked)}
        />
        Solo donde Farmacity pierde
      </label>
    </div>
  );
}
