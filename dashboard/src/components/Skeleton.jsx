export default function Skeleton({ count = 8 }) {
  return (
    <div className="products-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i} />
      ))}
    </div>
  );
}
