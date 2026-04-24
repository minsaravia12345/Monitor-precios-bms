import React, { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [productos, setProductos] = useState([]);
  const [filtroGrupo, setFiltroGrupo] = useState('Todos');
  const [filtroGanador, setFiltroGanador] = useState('Todos');

  useEffect(() => {
    fetch('/datos_consolidados.json')
      .then(res => res.json())
      .then(data => setProductos(data))
      .catch(err => console.error("Error cargando datos:", err));
  }, []);

  const grupos = ['Todos', ...new Set(productos.map(p => p.Grupo))];
  
  const productosFiltrados = productos.filter(p => {
    const matchGrupo = filtroGrupo === 'Todos' || p.Grupo === filtroGrupo;
    const matchGanador = filtroGanador === 'Todos' || p.Ganador.includes(filtroGanador);
    return matchGrupo && matchGanador;
  });

  const formatearPrecio = (num) => {
    return new Intl.NumberFormat('es-AR').format(num);
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <h1 className="title">SmartPrice Tracker</h1>
        <p className="subtitle">Comparativa en tiempo real: Central Oeste vs Farmacity</p>
      </header>

      <div className="filters">
        <select 
          className="filter-btn" 
          value={filtroGrupo} 
          onChange={(e) => setFiltroGrupo(e.target.value)}
        >
          {grupos.map(g => <option key={g} value={g}>{g}</option>)}
        </select>
        
        <button 
          className={`filter-btn ${filtroGanador === 'Todos' ? 'active' : ''}`}
          onClick={() => setFiltroGanador('Todos')}
        >Todos</button>
        <button 
          className={`filter-btn ${filtroGanador === 'Central Oeste' ? 'active' : ''}`}
          onClick={() => setFiltroGanador('Central Oeste')}
        >Gana Central Oeste</button>
        <button 
          className={`filter-btn ${filtroGanador === 'Farmacity' ? 'active' : ''}`}
          onClick={() => setFiltroGanador('Farmacity')}
        >Gana Farmacity</button>
      </div>

      <div className="products-grid">
        {productosFiltrados.map((prod, idx) => {
           const pCentral = prod.Precios.Central_Oeste;
           const pFarmacity = prod.Precios.Farmacity;
           
           return (
             <div className="product-card" key={prod.Id} style={{ animationDelay: `${idx * 0.05}s` }}>
               <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                 <span className="product-group">{prod.Grupo}</span>
                 {prod.EAN && prod.EAN !== 'N/A' && (
                   <span style={{fontSize: '0.7rem', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-secondary)'}}>
                     EAN: {prod.EAN}
                   </span>
                 )}
               </div>
               <h3 className="product-name">{prod.Nombre}</h3>
               
               <div className="prices-container">
                 {/* Central Oeste render */}
                 {pCentral ? (
                   <a href={pCentral.Link} target="_blank" rel="noreferrer" 
                      className={`pharmacy-price ${prod.Ganador.includes('Central Oeste') ? 'winner' : ''}`}>
                     <span className="pharmacy-name"> Central Oeste</span>
                     <div className="price-details">
                       <span className={`actual-price currency ${prod.Ganador.includes('Central Oeste') ? 'winner-text' : ''}`}>
                         {formatearPrecio(pCentral.Precio_Final)}
                         {pCentral.Descuento > 0 && <span className="discount-badge">-{pCentral.Descuento}%</span>}
                       </span>
                       {pCentral.Precio_Lista > pCentral.Precio_Final && (
                         <span className="list-price currency">{formatearPrecio(pCentral.Precio_Lista)}</span>
                       )}
                     </div>
                   </a>
                 ) : (
                   <div className="pharmacy-price" style={{opacity: 0.5}}>
                     <span className="pharmacy-name">Central Oeste</span>
                     <span className="price-details">No disponible</span>
                   </div>
                 )}

                 {/* Farmacity render */}
                 {pFarmacity ? (
                   <a href={pFarmacity.Link} target="_blank" rel="noreferrer" 
                      className={`pharmacy-price ${prod.Ganador.includes('Farmacity') ? 'winner' : ''}`}>
                     <span className="pharmacy-name">Farmacity</span>
                     <div className="price-details">
                       <span className={`actual-price currency ${prod.Ganador.includes('Farmacity') ? 'winner-text' : ''}`}>
                         {formatearPrecio(pFarmacity.Precio_Final)}
                         {pFarmacity.Descuento > 0 && <span className="discount-badge">-{pFarmacity.Descuento}%</span>}
                       </span>
                       {pFarmacity.Precio_Lista > pFarmacity.Precio_Final && (
                         <span className="list-price currency">{formatearPrecio(pFarmacity.Precio_Lista)}</span>
                       )}
                     </div>
                   </a>
                 ) : (
                   <div className="pharmacy-price" style={{opacity: 0.5}}>
                     <span className="pharmacy-name">Farmacity</span>
                     <span className="price-details">No disponible</span>
                   </div>
                 )}
               </div>

               <div className="card-footer">
                 <span className="winner-badge">{prod.Ganador === 'Empate' ? 'Empate' : `Recomendado`}</span>
                 {prod.Diferencia_Porcentual > 0 && (
                   <span className="difference">Ahorras {prod.Diferencia_Porcentual}%</span>
                 )}
               </div>
             </div>
           )
        })}
        {productosFiltrados.length === 0 && (
          <div style={{gridColumn: "1/-1", textAlign: "center", padding: "3rem", color: "var(--text-secondary)"}}>
            No se encontraron productos con los filtros seleccionados.
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
