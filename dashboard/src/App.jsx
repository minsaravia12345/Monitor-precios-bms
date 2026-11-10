import { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import StatsOverview from './components/StatsOverview';
import Toolbar from './components/Toolbar';
import ProductGrid from './components/ProductGrid';
import Pagination from './components/Pagination';
import EmptyState from './components/EmptyState';
import Skeleton from './components/Skeleton';
import Footer from './components/Footer';
import { useTheme } from './hooks/useTheme';
import { normalizarTexto, parseNumero } from './utils/format';
import './index.css';

const FARMACIAS = [
  { key: 'Central_Oeste', label: 'Central Oeste', color: '#60a5fa' },
  { key: 'Farmacity', label: 'Farmacity', color: '#f472b6' },
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
  const [sortBy, setSortBy] = useState('ahorro_desc');
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

  const grupos = useMemo(() => ['Todos', ...new Set(productos.map((p) => p.Grupo))], [productos]);

  const productosFiltrados = useMemo(() => {
    const term = normalizarTexto(search.trim());

    const filtrados = productos.filter((p) => {
      const matchTab = tabActivo === 'killers' ? p.Es_Killer : true;
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
      return (b.Diferencia_Porcentual || 0) - (a.Diferencia_Porcentual || 0);
    });
  }, [productos, tabActivo, filtroGrupo, filtroGanador, search, sortBy]);

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

  return (
    <>
      <Header ultimaActualizacion={ultimaActualizacion} theme={theme} onToggleTheme={toggleTheme} />

      <main className="app-shell">
        <div className="page-intro">
          <h2>Comparativa de precios</h2>
          <p>Seguimiento diario de precios en farmacias y marketplaces para detectar las mejores oportunidades.</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <Skeleton count={8} />
        ) : (
          <>
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

            <div className="results-meta">
              <span>
                <strong>{productosFiltrados.length}</strong> resultado
                {productosFiltrados.length !== 1 ? 's' : ''}
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
