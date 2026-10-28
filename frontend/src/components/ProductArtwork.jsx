const PRODUCT_ICONS = {
  P001: "🖱️",
  P002: "🎧",
  P003: "🔌",
  P004: "💻",
  P005: "⌨️",
  P006: "🔋",
  P007: "⌚",
  P008: "🔊",
  P009: "👕",
  P010: "👖",
  P011: "👟",
  P012: "🎒",
  P013: "👔",
  P014: "🧥",
  P015: "🧴",
  P016: "☕",
  P017: "💡",
  P018: "🛏️",
  P019: "🗄️",
  P020: "🍳",
  P021: "🧘",
  P022: "🏋️",
  P023: "⚽",
  P024: "🪢",
  P025: "📕",
  P026: "📘",
  P027: "📗",
  P028: "🚀",
  P029: "📓",
  P030: "🖊️",
  P031: "🖍️",
  P032: "🧴",
  P033: "🧴",
  P034: "🧼",
  P035: "💨",
};

const CATEGORY_COLORS = {
  Electronics: ["#e8eff1", "#78939a"],
  Fashion: ["#f3e9e4", "#b68779"],
  "Home & Kitchen": ["#f2eee2", "#ac9b68"],
  Sports: ["#e7efe4", "#78946e"],
  Books: ["#f0e9df", "#a88663"],
  Stationery: ["#eee8f2", "#9480a3"],
  Beauty: ["#f4e7e8", "#b7858e"],
};

export default function ProductArtwork({ product }) {
  const [background, accent] = CATEGORY_COLORS[product.category] || ["#edf0e9", "#8d9c84"];

  return (
    <svg
      className="product-artwork"
      viewBox="0 0 280 145"
      role="img"
      aria-label={`${product.product_name} illustration`}
    >
      <rect width="280" height="145" rx="8" fill={background} />
      <circle cx="224" cy="31" r="52" fill={accent} opacity=".13" />
      <circle cx="42" cy="124" r="42" fill={accent} opacity=".1" />
      <path d="M22 28h54M206 116h45" stroke={accent} strokeWidth="1" opacity=".28" />
      <text
        x="140"
        y="98"
        textAnchor="middle"
        fontSize="68"
        fontFamily="Segoe UI Emoji, Apple Color Emoji, sans-serif"
      >
        {PRODUCT_ICONS[product.product_id] || "✦"}
      </text>
      <text
        x="260"
        y="132"
        textAnchor="end"
        fill={accent}
        fontSize="9"
        fontFamily="DM Sans, sans-serif"
        fontWeight="700"
        letterSpacing="1"
      >
        {product.product_id}
      </text>
    </svg>
  );
}
