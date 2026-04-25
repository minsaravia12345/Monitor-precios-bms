import React, { useState, useEffect, useMemo } from 'react';
import './index.css';

const FARMACIAS = [
  { key: "Central_Oeste", label: "Central Oeste", color: "#93c5fd" },
  { key: "Farmacity",     label: "Farmacity",     color: "#f9a8d4" },
  { key: "Farmaonline",   label: "Farmaonline",   color: "#fcd34d" },
  { key: "MercadoLibre",   label: "MercadoLibre",   color: "#4ade80" },
];

function App() {
  const [productos, setProductos] = useState([]);
  const [ultimaActualizacion, setUltimaActualizacion] = useState('');
  const [tabActivo, setTabActivo] = useState('explorar'); // 'explorar' o 'killers'
  const [filtroGrupo, setFiltroGrupo] = useState('Todos');
  const [filtroGanador, setFiltroGanador] = useState('Todos');

  useEffect(() => {
    // Cache busting con timestamp para asegurar datos frescos
    fetch(`/datos_consolidados.json?t=${Date.now()}`)
      .then(res => res.json())
      .then(data => {
        const listado = data.productos || data;
        setUltimaActualizacion(data.ultima_actualizacion || '');
        setProductos(listado.map(p => ({ ...p, Es_Killer: !!p.Es_Killer })));
      })
      .catch(err => console.error("Error cargando datos:", err));
  }, []);

  const grupos = useMemo(() => ['Todos', ...new Set(productos.map(p => p.Grupo))], [productos]);
  
  const productosFiltrados = useMemo(() => {
    return productos.filter(p => {
      const matchTab = tabActivo === 'killers' ? p.Es_Killer : true;
      const matchGrupo = filtroGrupo === 'Todos' || String(p.Grupo) === String(filtroGrupo);
      const matchGanador = filtroGanador === 'Todos' || (p.Ganador && String(p.Ganador).includes(filtroGanador));
      return matchTab && matchGrupo && matchGanador;
    });
  }, [productos, tabActivo, filtroGrupo, filtroGanador]);

  // Stats
  const stats = useMemo(() => {
    const s = { total: productos.length, co: 0, fa: 0, fo: 0, ml: 0, empate: 0, killers: 0 };
    productos.forEach(p => {
      if (p.Es_Killer) s.killers++;
      if (p.Ganador && p.Ganador.includes("Central")) s.co++;
      else if (p.Ganador && p.Ganador.includes("Farmacity")) s.fa++;
      else if (p.Ganador && p.Ganador.includes("Farmaonline")) s.fo++;
      else if (p.Ganador && p.Ganador.includes("MercadoLibre")) s.ml++;
      else if (p.Ganador === "Empate") s.empate++;
    });
    return s;
  }, [productos]);

  const formatearPrecio = (num) => {
    if (!num || num === Infinity) return "-";
    return new Intl.NumberFormat('es-AR').format(num);
  }

  const renderPharmacy = (prod, farmKey, farmLabel) => {
    const pData = prod.Precios[farmKey];
    const isWinner = prod.Ganador && prod.Ganador.includes(farmLabel.replace("_", " "));
    
    if (!pData) return (
      <div className="pharmacy-price" key={farmKey}>
        <span className="pharmacy-name">{farmLabel}</span>
        <span className="no-avail">No disponible</span>
      </div>
    );

    return (
      <a href={pData.Link} target="_blank" rel="noreferrer" key={farmKey}
         className={`pharmacy-price ${isWinner ? 'winner' : ''}`}>
        <span className="pharmacy-name">{farmLabel}</span>
        <div className="price-details">
          <span className={`actual-price currency ${isWinner ? 'winner-text' : ''}`}>
            {formatearPrecio(pData.Precio_Final)}
            {pData.Descuento > 0 && <span className="discount-badge">-{pData.Descuento}%</span>}
          </span>
          {pData.Precio_Lista > pData.Precio_Final && (
            <span className="list-price currency">{formatearPrecio(pData.Precio_Lista)}</span>
          )}
        </div>
      </a>
    );
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1 className="title">SmartPrice Tracker</h1>
        <p className="subtitle">Comparativa Multi-Farmacia & MercadoLibre</p>
        {ultimaActualizacion && <p style={{fontSize:'0.8rem', opacity:0.7, marginTop:'5px'}}>Sincronizado: {ultimaActualizacion}</p>}
      </header>

      <div className="stats-bar">
        <div className="stat-card" onClick={() => setTabActivo('explorar')} style={{cursor:'pointer', border: tabActivo === 'explorar' ? '1px solid var(--accent-color)' : ''}}>
            <div className="stat-num" style={{color:'#f8fafc'}}>{stats.total}</div>
            <div className="stat-label">Explorar Todo</div>
        </div>
        <div className="stat-card" onClick={() => setTabActivo('killers')} style={{cursor:'pointer', border: tabActivo === 'killers' ? '1px solid #4ade80' : ''}}>
            <div className="stat-num" style={{color:'#4ade80'}}>{stats.killers}</div>
            <div className="stat-label">Killers (Estrategia)</div>
        </div>
        <div className="stat-card"><div className="stat-num co">{stats.co}</div><div className="stat-label">CO</div></div>
        <div className="stat-card"><div className="stat-num fa">{stats.fa}</div><div className="stat-label">Fcty</div></div>
        <div className="stat-card"><div className="stat-num fo">{stats.fo}</div><div className="stat-label">FO</div></div>
        <div className="stat-card"><div className="stat-num ml" style={{color:'#22c55e'}}>{stats.ml}</div><div className="stat-label">ML</div></div>
      </div>

      <div className="filters">
        <div style={{display:'flex', gap:'10px', alignItems:'center', background:'var(--card-bg)', padding:'5px 15px', borderRadius:'30px', border:'1px solid var(--card-border)'}}>
            <button className={`filter-btn ${tabActivo === 'explorar' ? 'active' : ''}`} onClick={() => setTabActivo('explorar')}>Explorar Todo</button>
            <button className={`filter-btn ${tabActivo === 'killers' ? 'active' : ''}`} onClick={() => setTabActivo('killers')} style={{borderColor: tabActivo === 'killers' ? '#22c55e' : ''}}>Pestaña Killers</button>
        </div>

        <select className="filter-btn" value={filtroGrupo} onChange={(e) => setFiltroGrupo(e.target.value)}>
          {grupos.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
        
        <button className={`filter-btn ${filtroGanador === 'Todos' ? 'active' : ''}`} onClick={() => setFiltroGanador('Todos')}>Cualquier Ganador</button>
        <button className={`filter-btn ${filtroGanador === 'MercadoLibre' ? 'active' : ''}`} onClick={() => setFiltroGanador('MercadoLibre')}>Gana ML</button>
      </div>

      <div className="products-grid">
        {productosFiltrados.map((prod, idx) => (
          <div className={`product-card ${prod.Es_Killer ? 'killer-style' : ''}`} key={prod.Id} style={{ animationDelay: `${(idx % 20) * 0.02}s` }}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
              <span className="product-group">{prod.Es_Killer ? '🎯 Killer Item' : prod.Grupo}</span>
              {prod.EAN && prod.EAN !== 'N/A' && (
                <span style={{fontSize: '0.65rem', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-secondary)'}}>
                  EAN: {prod.EAN}
                </span>
              )}
            </div>
            <h3 className="product-name">{prod.Nombre}</h3>
            
            <div className="prices-container">
              {FARMACIAS.map(f => renderPharmacy(prod, f.key, f.label))}
            </div>

            <div className="card-footer">
              <span className="winner-badge">{prod.Ganador === 'Empate' ? 'Empate' : `Gana ${prod.Ganador}`}</span>
              {prod.Diferencia_Porcentual > 0 && (
                <span className="difference">Ahorro Máx: {prod.Diferencia_Porcentual}%</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
