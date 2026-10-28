import ProductArtwork from "./ProductArtwork.jsx";

export default function ProductCard({ product, selected, onSelect, score, reason }) {
  return (
    <button
      className={`product-card${selected ? " product-card-selected" : ""}`}
      onClick={() => onSelect(product.product_id)}
      type="button"
      aria-pressed={selected}
    >
      <div className="product-card-top">
        <span className="category-chip">{product.category}</span>
        <span className="product-id">{product.product_id}</span>
      </div>
      <ProductArtwork product={product} />
      <h3>{product.product_name}</h3>
      <div className="product-meta">
        {product.price_inr != null && (
          <span>₹{Number(product.price_inr).toLocaleString("en-IN")}</span>
        )}
        <span>★ {Number(product.average_rating).toFixed(1)} ({product.rating_count})</span>
      </div>
      {score !== undefined && (
        <div className="recommendation-meta">
          <span className="score-pill">{Math.round(score * 100)} match</span>
          <span>{reason}</span>
        </div>
      )}
    </button>
  );
}
