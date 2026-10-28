import { useEffect, useState } from "react";
import ProductCard from "./components/ProductCard.jsx";
import {
  getHealth,
  getProduct,
  getProductRecommendations,
  getProducts,
  getUserRecommendations,
} from "./services/api.js";

function ProductTile({ item, onSelect }) {
  return (
    <ProductCard
      product={item.product}
      onSelect={onSelect}
      score={item.score}
      reason={item.reason}
    />
  );
}

export default function App() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [recommendationMode, setRecommendationMode] = useState("product");
  const [userId, setUserId] = useState("U001");
  const [maxPrice, setMaxPrice] = useState("");
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [error, setError] = useState("");
  const [recommendationError, setRecommendationError] = useState("");

  useEffect(() => {
    getProducts()
      .then((result) => {
        setCategories([...new Set(result.items.map((product) => product.category))].sort());
      })
      .catch((requestError) => setError(requestError.message));
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getProducts({ q: query.trim(), category })
      .then((result) => {
        if (!active) return;
        setProducts(result.items);
        setSelectedId((current) =>
          result.items.some((product) => product.product_id === current)
            ? current
            : result.items[0]?.product_id || "",
        );
        setError("");
      })
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [query, category]);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelectedProduct(null);
      setRecommendations([]);
      return;
    }
    let active = true;
    setRecommendationLoading(true);
    setRecommendationError("");
    Promise.all([
      getProduct(selectedId),
      getProductRecommendations(selectedId),
    ])
      .then(([product, result]) => {
        if (!active) return;
        setSelectedProduct(product);
        setRecommendations(result.items);
      })
      .catch((requestError) => active && setRecommendationError(requestError.message))
      .finally(() => active && setRecommendationLoading(false));
    return () => {
      active = false;
    };
  }, [selectedId]);

  async function loadUserRecommendations(event) {
    event.preventDefault();
    setRecommendationLoading(true);
    setRecommendationError("");
    setRecommendationMode("user");
    try {
      const result = await getUserRecommendations(userId.trim(), maxPrice);
      setRecommendations(result.items);
      setSelectedProduct(null);
      if (result.items.length === 0) setRecommendationError(result.message);
    } catch (requestError) {
      setRecommendations([]);
      setRecommendationError(requestError.message);
    } finally {
      setRecommendationLoading(false);
    }
  }

  function chooseProduct(productId) {
    setRecommendationMode("product");
    setSelectedId(productId);
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#" aria-label="Product recommendation home">
          <span className="brand-mark">P</span>
          <span>Product<span className="brand-light">ly</span></span>
        </a>
        <nav aria-label="Main navigation">
          <a className="active" href="#discover">Discover</a>
          <a href="#recommendations">Recommendations</a>
          <a href="#about">How it works</a>
        </nav>
        <span className="topbar-status"><i /> Recommendation engine</span>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">A LITTLE MORE PERSONAL</span>
          <h1>Find your next<br /><em>favorite thing.</em></h1>
          <p>Explore a curated catalog and discover products connected by what people like you rate highly.</p>
          <a className="hero-link" href="#discover">Explore the collection <span>↓</span></a>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="hero-card hero-card-main"><span>OUR PICK</span><strong>Good finds,<br />better fit.</strong><i>✳</i></div>
          <div className="hero-card hero-card-float">✦ <span>Made for discovery</span></div>
          <div className="hero-spark">✳</div>
        </div>
        <div className="hero-stats">
          <div><strong>{health?.product_count ?? "—"}</strong><span>thoughtful finds</span></div>
          <div><strong>{health?.interaction_count ?? "—"}</strong><span>ratings considered</span></div>
          <div><strong>{health ? "01" : "—"}</strong><span>smart discovery engine</span></div>
        </div>
      </section>

      <section className="catalog-section" id="discover">
        <div className="section-heading">
          <div><span className="eyebrow">THE COLLECTION</span><h2>Browse the good stuff</h2></div>
          <span className="result-count">{products.length} products shown</span>
        </div>
        <div className="filters">
          <label className="search-box">
            <span aria-hidden="true">⌕</span>
            <input
              aria-label="Search products"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search products or categories"
              value={query}
            />
          </label>
          <label className="category-select">
            <span className="sr-only">Filter by category</span>
            <select onChange={(event) => setCategory(event.target.value)} value={category}>
              <option value="">All categories</option>
              {categories.map((value) => <option key={value} value={value}>{value}</option>)}
            </select>
          </label>
        </div>
        {error && <div className="notice error-notice">{error}</div>}
        {loading ? <div className="loading-state"><span className="spinner" /> Loading products…</div> :
          products.length ? (
            <div className="product-grid">
              {products.map((product) => (
                <ProductCard
                  key={product.product_id}
                  product={product}
                  selected={recommendationMode === "product" && selectedId === product.product_id}
                  onSelect={chooseProduct}
                />
              ))}
            </div>
          ) : !error ? <div className="empty-state">No products match that search. Try another name or category.</div> : null}
      </section>

      <section className="recommendation-section" id="recommendations">
        <div className="recommendation-header">
          <div><span className="eyebrow">YOUR DISCOVERY LIST</span><h2>Recommended for you<span>.</span></h2></div>
          <div className="mode-toggle" aria-label="Recommendation mode">
            <button
              className={recommendationMode === "product" ? "mode-active" : ""}
              onClick={() => setRecommendationMode("product")}
              type="button"
            >Similar products</button>
            <button
              className={recommendationMode === "user" ? "mode-active" : ""}
              onClick={() => setRecommendationMode("user")}
              type="button"
            >For a user</button>
          </div>
        </div>
        {recommendationMode === "product" && selectedProduct && (
          <div className="selected-product">
            <div><span className="eyebrow">YOU’RE EXPLORING</span><strong>{selectedProduct.product_name}</strong></div>
            <span>
              {selectedProduct.category}
              {selectedProduct.price_inr != null && ` · ₹${Number(selectedProduct.price_inr).toLocaleString("en-IN")}`}
            </span>
          </div>
        )}
        {recommendationMode === "user" && (
          <form className="user-form" onSubmit={loadUserRecommendations}>
            <label htmlFor="user-id">User ID</label>
            <input id="user-id" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="e.g. U001" required />
            <label htmlFor="max-price">Max budget (INR)</label>
            <input
              id="max-price"
              type="number"
              min="0"
              max="1000000"
              step="1"
              value={maxPrice}
              onChange={(event) => setMaxPrice(event.target.value)}
              placeholder="Enter your budget"
              required
            />
            <button className="primary-button" disabled={recommendationLoading} type="submit">Recommend products <span>→</span></button>
            <span className="budget-hint">Only products at or below your budget are shown.</span>
          </form>
        )}
        {recommendationLoading ? <div className="loading-state"><span className="spinner" /> Finding your next favorite…</div> :
          recommendationError ? <div className="empty-state">{recommendationError}</div> :
            recommendations.length ? (
              <>
                <div className="recommendation-grid">
                  {recommendations.map((item) => (
                    <ProductTile key={item.product.product_id} item={item} onSelect={chooseProduct} />
                  ))}
                </div>
                <p className="recommendation-footnote">
                  {recommendationMode === "user"
                    ? "Based on recorded ratings; products already rated by this user are excluded."
                    : "Selected product excluded. Scores reflect learned similarity, not purchase probability."}
                </p>
              </>
            ) : <div className="empty-state">Select a product above to see similar finds.</div>}
      </section>

      <section className="about-section" id="about">
        <div className="about-icon">✳</div>
        <div><span className="eyebrow">THOUGHTFUL BY DESIGN</span><h2>Recommendations with a reason.</h2>
          <p>The engine blends patterns in user ratings with product names and categories. When rating-based signals are weak, it falls back to products with stronger average ratings, adjusted for how many people rated them. The product illustrations are display-only; images are not model inputs. The dataset includes no personal demographics or purchase history.</p>
        </div>
        <div className="method-card">
          <span>THE METHOD</span><strong>{health?.method ? "Hybrid item similarity" : "Loading model details"}</strong>
          <small>{health ? `${health.product_count} products · ${health.interaction_count} ratings` : "Connect to the API to view model status"}</small>
        </div>
      </section>

      <footer><span>Productly <i>✳</i></span><span>Product discovery, made a little more delightful.</span><a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">API documentation ↗</a></footer>
    </main>
  );
}
