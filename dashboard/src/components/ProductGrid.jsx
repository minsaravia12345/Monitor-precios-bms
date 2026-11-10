import ProductCard from './ProductCard';

export default function ProductGrid({ productos, farmacias }) {
  return (
    <div className="products-grid">
      {productos.map((prod, idx) => (
        <ProductCard
          producto={prod}
          farmacias={farmacias}
          key={prod.Id}
          delay={(idx % 24) * 0.02}
        />
      ))}
    </div>
  );
}
