import { IconInbox } from './Icons';

export default function EmptyState({ onClear }) {
  return (
    <div className="empty-state">
      <IconInbox />
      <h3>No encontramos productos</h3>
      <p>Probá con otra búsqueda o quitá algunos filtros para ver más resultados.</p>
      <button type="button" onClick={onClear}>
        Limpiar filtros
      </button>
    </div>
  );
}
