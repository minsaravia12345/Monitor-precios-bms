import { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import BriefingPanel from './components/BriefingPanel';
import IntelligenceSummary from './components/IntelligenceSummary';
import StatsOverview from './components/StatsOverview';
import Toolbar from './components/Toolbar';
import ProductGrid from './components/ProductGrid';
import Pagination from './components/Pagination';
import EmptyState from './components/EmptyState';
import Skeleton from './components/Skeleton';
import Footer from './components/Footer';
import { useTheme } from './hooks/useTheme';
import { normalizarTexto, parseNumero } from './utils/format';
import { calcularMetricas, diagnosticoCombinado } from './utils/metrics';
import './index.css';

const UMBRAL_OPORTUNIDAD = 60;

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

  const filterKey = `${tabActivo}|${search}|${filtroGrupo}|${filtroGanador}|${sortBy}`;
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
    () =>
      productos.map((p) => {
        const metricas = calcularMetricas(p, farmaciasVisibles.length || 1);
        const diagnostico = diagnosticoCombinado(metricas.priceIndex, metricas.promoPressure);
        return { ...p, metricas, diagnostico };
      }),
    [productos, farmaciasVisibles]
  );

  const grupos = useMemo(() => ['Todos', ...new Set(productos.map((p) => p.Grupo))], [productos]);

  const productosFiltrados = useMemo(() => {
    const term = normalizarTexto(search.trim());

    const filtrados = productosConMetricas.filter((p) => {
      const matchTab = tabActivo === 'killers' ? p.metricas.mos >= UMBRAL_OPORTUNIDAD : true;
      const matchGrupo = filtroGrupo === 'Todos' || String(p.Grupo) === String(filtroGrupo);
      const matchGanador =
        filtroGanador === 'Todos' || (p.Ganador && String(p.Ganador).includes(filtroGanador));
      const matchSearch =
        !term ||
        normalizarTexto(p.Nombre).includes(term) ||
        normalizarTexto(p.EAN).includes(term);
      return matchTab && matchGrupo && matchGanador && matchSearch;
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
  }, [productosConMetricas, tabActivo, filtroGrupo, filtroGanador, search, sortBy]);

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
    const oportunidadesCriticas = productosConMetricas.filter((p) => p.metricas.mos >= 80).length;
    return { priceIndex, promoPressure, visibilityIndex, mos, oportunidadesCriticas };
  }, [productosConMetricas]);

  const briefing = useMemo(() => {
    const empujarFuerte = productosConMetricas.filter((p) => p.metricas.mos >= 80).length;
    const empujarSelectivo = productosConMetricas.filter((p) => p.metricas.mos >= 60 && p.metricas.mos < 80).length;
    const riesgoPerdida = productosConMetricas.filter((p) => p.diagnostico.tone === 'critical').length;
    const topOportunidades = [...productosConMetricas].sort((a, b) => b.metricas.mos - a.metricas.mos).slice(0, 5);
    return { counts: { empujarFuerte, empujarSelectivo, riesgoPerdida }, topOportunidades };
  }, [productosConMetricas]);

  const limpiarFiltros = () => {
    setSearch('');
    setFiltroGrupo('Todos');
    setFiltroGanador('Todos');
    setTabActivo('explorar');
  };

  const hayFiltrosActivos =
    Boolean(search) || filtroGrupo !== 'Todos' || filtroGanador !== 'Todos' || tabActivo !== 'explorar';

  const handlePageChange = (p) => {
    setPage(p);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSeleccionarProducto = (producto) => {
    setTabActivo('explorar');
    setFiltroGrupo('Todos');
    setFiltroGanador('Todos');
    setSearch(producto.EAN && producto.EAN !== 'N/A' ? producto.EAN : producto.Nombre);
    setTimeout(() => {
      document.getElementById('catalogo')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 50);
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
            <BriefingPanel
              counts={briefing.counts}
              topOportunidades={briefing.topOportunidades}
              onSeleccionarProducto={handleSeleccionarProducto}
            />

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
            />

            <div id="catalogo" className="results-meta">
              <span>
                <strong>{productosFiltrados.length}</strong> resultado
                {productosFiltrados.length !== 1 ? 's' : ''}
                {tabActivo === 'killers' && ` con Market Opportunity Score ≥ ${UMBRAL_OPORTUNIDAD}`}
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
