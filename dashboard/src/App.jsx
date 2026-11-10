import { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import IntelligenceSummary from './components/IntelligenceSummary';
import StatsOverview from './components/StatsOverview';
import Toolbar from './components/Toolbar';
import AdvancedFilters from './components/AdvancedFilters';
import ProductGrid from './components/ProductGrid';
import Pagination from './components/Pagination';
import EmptyState from './components/EmptyState';
import Skeleton from './components/Skeleton';
import Footer from './components/Footer';
import { useTheme } from './hooks/useTheme';
import { normalizarTexto, parseNumero } from './utils/format';
import { calcularMetricas } from './utils/metrics';
import './index.css';

const FARMACIAS = [
  { key: 'Farmacity', label: 'Farmacity', color: '#f472b6' },
  { key: 'Central_Oeste', label: 'Central Oeste', color: '#60a5fa' },
  { key: 'Farmaonline', label: 'Farmaonline', color: '#fbbf24' },
  { key: 'MercadoLibre', label: 'MercadoLibre', color: '#34d399' },
];

const PAGE_SIZE = 24;

function App() {
  const { theme, toggleTheme } = useTheme();

  const [productos, setProductos] = useState([]);
  const [ultimaActualizacion, setUltimaActualizacion] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [tabActivo, setTabActivo] = useState('explorar');
  const [search, setSearch] = useState('');
  const [filtroGrupo, setFiltroGrupo] = useState('Todos');
  const [filtroGanador, setFiltroGanador] = useState('Todos');
  const [sortBy, setSortBy] = useState('mos_desc');
  const [page, setPage] = useState(1);

  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filtroStock, setFiltroStock] = useState('Todos');
  const [filtroBrechaMin, setFiltroBrechaMin] = useState(0);
  const [filtroDescuento, setFiltroDescuento] = useState('Todos');
  const [soloPerdiendo, setSoloPerdiendo] = useState(false);
  const [filtroPrecioRango, setFiltroPrecioRango] = useState('Todos');

  const filterKey = `${tabActivo}|${search}|${filtroGrupo}|${filtroGanador}|${sortBy}|${filtroStock}|${filtroBrechaMin}|${filtroDescuento}|${soloPerdiendo}|${filtroPrecioRango}`;
  const [lastFilterKey, setLastFilterKey] = useState(filterKey);
  if (filterKey !== lastFilterKey) {
    setLastFilterKey(filterKey);
    setPage(1);
  }

  useEffect(() => {
    fetch(`/datos_consolidados.json?t=${Date.now()}`)
      .then((res) => {
        if (!res.ok) throw new Error('Respuesta no válida del servidor');
        return res.json();
      })
      .then((data) => {
        const listado = data.productos || data;
        setUltimaActualizacion(data.ultima_actualizacion || '');
        setProductos(listado.map((p) => ({ ...p, Es_Killer: !!p.Es_Killer })));
      })
      .catch((err) => {
        console.error('Error cargando datos:', err);
        setError('No pudimos cargar los datos de precios. Probá recargar la página.');
      })
      .finally(() => setLoading(false));
  }, []);

  const farmaciasVisibles = useMemo(
    () => FARMACIAS.filter((f) => productos.some((p) => p.Precios && p.Precios[f.key])),
    [productos]
  );

  const productosConMetricas = useMemo(
    () => productos.map((p) => ({ ...p, metricas: calcularMetricas(p, farmaciasVisibles.length || 1) })),
    [productos, farmaciasVisibles]
  );

  const grupos = useMemo(() => ['Todos', ...new Set(productos.map((p) => p.Grupo))], [productos]);

  const productosFiltrados = useMemo(() => {
    const term = normalizarTexto(search.trim());

    const filtrados = productosConMetricas.filter((p) => {
      const matchTab = tabActivo === 'killers' ? p.metricas.mos >= 65 : true;
      const matchGrupo = filtroGrupo === 'Todos' || String(p.Grupo) === String(filtroGrupo);
      const matchGanador =
        filtroGanador === 'Todos' || (p.Ganador && String(p.Ganador).includes(filtroGanador));
      const matchSearch =
        !term ||
        normalizarTexto(p.Nombre).includes(term) ||
        normalizarTexto(p.EAN).includes(term);

      const datosFarmacity = p.Precios?.Farmacity;
      const matchStock =
        filtroStock === 'Todos' ||
        (filtroStock === 'No comercializado' && !datosFarmacity) ||
        (filtroStock === 'Con stock' && datosFarmacity?.Stock === 'Con Stock') ||
        (filtroStock === 'Sin stock' && datosFarmacity && datosFarmacity.Stock !== 'Con Stock');

      const matchDescuento =
        filtroDescuento === 'Todos' ||
        (filtroDescuento === 'Con descuento' && Number(datosFarmacity?.Descuento) > 0) ||
        (filtroDescuento === 'Sin descuento' && !(Number(datosFarmacity?.Descuento) > 0));

      const matchBrecha = (p.Diferencia_Porcentual || 0) >= filtroBrechaMin;

      const matchPerdiendo =
        !soloPerdiendo ||
        (!!datosFarmacity && !(p.Ganador && String(p.Ganador).includes('Farmacity')));

      const mejorPrecio = parseNumero(p.MejorPrecio);
      const matchPrecio =
        filtroPrecioRango === 'Todos' ||
        (mejorPrecio !== null &&
          ((filtroPrecioRango === 'bajo' && mejorPrecio < 15000) ||
            (filtroPrecioRango === 'medio' && mejorPrecio >= 15000 && mejorPrecio <= 50000) ||
            (filtroPrecioRango === 'alto' && mejorPrecio > 50000)));

      return (
        matchTab &&
        matchGrupo &&
        matchGanador &&
        matchSearch &&
        matchStock &&
        matchDescuento &&
        matchBrecha &&
        matchPerdiendo &&
        matchPrecio
      );
    });

    return [...filtrados].sort((a, b) => {
      if (sortBy === 'nombre_asc') return a.Nombre.localeCompare(b.Nombre);
      if (sortBy === 'precio_asc') {
        const pa = parseNumero(a.MejorPrecio) ?? Infinity;
        const pb = parseNumero(b.MejorPrecio) ?? Infinity;
        return pa - pb;
      }
      if (sortBy === 'price_index_desc') {
        const pa = a.metricas.priceIndex ?? -1;
        const pb = b.metricas.priceIndex ?? -1;
        return pb - pa;
      }
      if (sortBy === 'promo_desc') return b.metricas.promoPressure - a.metricas.promoPressure;
      if (sortBy === 'ahorro_desc') return (b.Diferencia_Porcentual || 0) - (a.Diferencia_Porcentual || 0);
      return b.metricas.mos - a.metricas.mos;
    });
  }, [
    productosConMetricas,
    tabActivo,
    filtroGrupo,
    filtroGanador,
    search,
    sortBy,
    filtroStock,
    filtroBrechaMin,
    filtroDescuento,
    soloPerdiendo,
    filtroPrecioRango,
  ]);

  const totalPages = Math.max(1, Math.ceil(productosFiltrados.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);

  const productosPagina = useMemo(
    () => productosFiltrados.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [productosFiltrados, currentPage]
  );

  const stats = useMemo(() => {
    const killers = productos.filter((p) => p.Es_Killer).length;
    const porFarmacia = farmaciasVisibles.map((f) => ({
      ...f,
      count: productos.filter((p) => p.Ganador && p.Ganador.includes(f.label)).length,
    }));
    return { total: productos.length, killers, porFarmacia };
  }, [productos, farmaciasVisibles]);

  const intel = useMemo(() => {
    if (productosConMetricas.length === 0) {
      return { priceIndex: null, promoPressure: 0, visibilityIndex: 0, mos: 0, oportunidadesCriticas: 0 };
    }
    const conPriceIndex = productosConMetricas.filter((p) => p.metricas.priceIndex !== null);
    const priceIndex = conPriceIndex.length
      ? Math.round(conPriceIndex.reduce((sum, p) => sum + p.metricas.priceIndex, 0) / conPriceIndex.length)
      : null;
    const promoPressure = Math.round(
      productosConMetricas.reduce((sum, p) => sum + p.metricas.promoPressure, 0) / productosConMetricas.length
    );
    const visibilityIndex = Math.round(
      productosConMetricas.reduce((sum, p) => sum + p.metricas.visibilityIndex, 0) / productosConMetricas.length
    );
    const mos = Math.round(
      productosConMetricas.reduce((sum, p) => sum + p.metricas.mos, 0) / productosConMetricas.length
    );
    const oportunidadesCriticas = productosConMetricas.filter((p) => p.metricas.mos >= 65).length;
    return { priceIndex, promoPressure, visibilityIndex, mos, oportunidadesCriticas };
  }, [productosConMetricas]);

  const limpiarFiltros = () => {
    setSearch('');
    setFiltroGrupo('Todos');
    setFiltroGanador('Todos');
    setTabActivo('explorar');
    setFiltroStock('Todos');
    setFiltroBrechaMin(0);
    setFiltroDescuento('Todos');
    setSoloPerdiendo(false);
    setFiltroPrecioRango('Todos');
  };

  const advancedCount =
    (filtroStock !== 'Todos' ? 1 : 0) +
    (filtroBrechaMin > 0 ? 1 : 0) +
    (filtroDescuento !== 'Todos' ? 1 : 0) +
    (soloPerdiendo ? 1 : 0) +
    (filtroPrecioRango !== 'Todos' ? 1 : 0);

  const hayFiltrosActivos =
    Boolean(search) ||
    filtroGrupo !== 'Todos' ||
    filtroGanador !== 'Todos' ||
    tabActivo !== 'explorar' ||
    advancedCount > 0;

  const handlePageChange = (p) => {
    setPage(p);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <Header ultimaActualizacion={ultimaActualizacion} theme={theme} onToggleTheme={toggleTheme} />

      <main className="app-shell">
        <div className="page-intro">
          <h2>Inteligencia competitiva de precios</h2>
          <p>
            Monitoreo diario de Central Oeste, Farmaonline y MercadoLibre para detectar riesgos y
            oportunidades de reprecificación frente a Farmacity.
          </p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <Skeleton count={8} />
        ) : (
          <>
            <h3 className="section-label">Indicadores de inteligencia competitiva</h3>
            <IntelligenceSummary
              priceIndex={intel.priceIndex}
              promoPressure={intel.promoPressure}
              visibilityIndex={intel.visibilityIndex}
              mos={intel.mos}
              oportunidadesCriticas={intel.oportunidadesCriticas}
            />

            <h3 className="section-label">Resumen del catálogo</h3>
            <StatsOverview total={stats.total} killers={stats.killers} porFarmacia={stats.porFarmacia} />

            <Toolbar
              tabActivo={tabActivo}
              setTabActivo={setTabActivo}
              search={search}
              setSearch={setSearch}
              grupos={grupos}
              filtroGrupo={filtroGrupo}
              setFiltroGrupo={setFiltroGrupo}
              farmaciasVisibles={farmaciasVisibles}
              filtroGanador={filtroGanador}
              setFiltroGanador={setFiltroGanador}
              sortBy={sortBy}
              setSortBy={setSortBy}
              filtersOpen={filtersOpen}
              onToggleFilters={() => setFiltersOpen((v) => !v)}
              advancedCount={advancedCount}
            />

            {filtersOpen && (
              <div id="advanced-filters-panel">
                <AdvancedFilters
                  filtroStock={filtroStock}
                  setFiltroStock={setFiltroStock}
                  filtroBrechaMin={filtroBrechaMin}
                  setFiltroBrechaMin={setFiltroBrechaMin}
                  filtroDescuento={filtroDescuento}
                  setFiltroDescuento={setFiltroDescuento}
                  filtroPrecioRango={filtroPrecioRango}
                  setFiltroPrecioRango={setFiltroPrecioRango}
                  soloPerdiendo={soloPerdiendo}
                  setSoloPerdiendo={setSoloPerdiendo}
                />
              </div>
            )}

            <div className="results-meta">
              <span>
                <strong>{productosFiltrados.length}</strong> resultado
                {productosFiltrados.length !== 1 ? 's' : ''}
                {tabActivo === 'killers' && ' con Market Opportunity Score ≥ 65'}
              </span>
              {hayFiltrosActivos && (
                <button type="button" className="clear-filters-btn" onClick={limpiarFiltros}>
                  Limpiar filtros
                </button>
              )}
            </div>

            {productosFiltrados.length === 0 ? (
              <EmptyState onClear={limpiarFiltros} />
            ) : (
              <>
                <ProductGrid productos={productosPagina} farmacias={farmaciasVisibles} />
                <Pagination page={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
              </>
            )}
          </>
        )}

        <Footer
          ultimaActualizacion={ultimaActualizacion}
          totalVisible={productosFiltrados.length}
          totalGeneral={productos.length}
        />
      </main>
    </>
  );
}

export default App;
