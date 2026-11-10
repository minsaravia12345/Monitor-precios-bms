import { IconChevronLeft, IconChevronRight } from './Icons';

function buildPageList(current, total) {
  const pages = [];
  const windowSize = 1;
  const add = (p) => pages.push(p);

  add(1);
  if (current - windowSize > 2) add('...');
  for (let p = Math.max(2, current - windowSize); p <= Math.min(total - 1, current + windowSize); p++) {
    add(p);
  }
  if (current + windowSize < total - 1) add('...');
  if (total > 1) add(total);

  return pages;
}

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  const pages = buildPageList(page, totalPages);

  return (
    <nav className="pagination" aria-label="Paginación de resultados">
      <button
        type="button"
        className="page-btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        aria-label="Página anterior"
      >
        <IconChevronLeft width={16} height={16} />
      </button>

      {pages.map((p, idx) =>
        p === '...' ? (
          <span className="page-ellipsis" key={`e-${idx}`}>
            …
          </span>
        ) : (
          <button
            type="button"
            key={p}
            className={`page-btn ${p === page ? 'active' : ''}`}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        )
      )}

      <button
        type="button"
        className="page-btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page === totalPages}
        aria-label="Página siguiente"
      >
        <IconChevronRight width={16} height={16} />
      </button>
    </nav>
  );
}
