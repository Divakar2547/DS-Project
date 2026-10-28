# Product Recommendation System

A small, full-stack product discovery application built around the supplied
`product_recommendation_dataset_700.csv`. The Python pipeline validates and
preprocesses the real file, trains a hybrid recommender and evaluates a
rating-based top-K ranking. FastAPI serves the generated catalog and model;
React/Vite consumes those endpoints.

## Dataset and provenance

- **File used:** `product_recommendation_dataset_700.csv` in the project root.
- **Research source URL and usage terms:** not included in the project request or
  with the supplied file. No external dataset is downloaded or substituted.
  The local file is used as provided. Confirm the original source and its license
  or usage terms before redistributing this project or publishing the data.
- **Verified shape:** 700 rows and 7 columns; 100 distinct users and 35 products.
- **Columns:** `interaction_id`, `user_id`, `product_id`, `rating`,
  `product_name`, `category`, `price_inr`.
- Every column is populated in the supplied CSV. There are no exact duplicate
  rows, repeated interaction IDs, or repeated user-product pairs. Ratings range
  from 1 to 5; product metadata is consistent per product ID.
- The file contains no product photos, descriptions, or review text. The UI
  includes local, product-ID-mapped SVG emoji illustrations (not source dataset
  photos) alongside names, categories, INR prices, and rating summaries computed
  from the interactions. Illustrations are display-only and are not model inputs.

The pipeline records its schema, input data types, missing counts, duplicate
count, rating distribution, cleaning counts, and train/test metrics in
`backend/artifacts/evaluation.json`.

## Architecture and data flow

1. `backend/scripts/train.py` reads and validates the root CSV.
2. Cleaned interaction and product tables are written to
   `backend/data/processed/`.
3. A compact JSON model artifact containing the catalog, item similarities,
   popularity priors, and observed user ratings is written to
   `backend/artifacts/recommender.json`.
4. FastAPI loads that artifact once at application startup. Requests do not
   retrain the model.
5. The Vite frontend makes HTTP requests to FastAPI; it contains no recommendation
   algorithm or simulated catalog.

```text
backend/
  app/
    main.py                 FastAPI endpoints and CORS
    schemas.py              Response validation
    services/recommender.py Inference from the saved model
  scripts/train.py          Cleaning, model training, evaluation
  tests/                    Model and API tests
frontend/
  src/                      React interface and API client
product_recommendation_dataset_700.csv
```

## Preprocessing and recommendation method

The loader checks for every required column and fails clearly if one is missing.
It trims identifier and descriptive text, removes exact duplicate records,
coerces ratings/prices to numeric types, drops rows with missing identifiers or
invalid/missing ratings, and rejects ratings outside 1–5, negative prices,
conflicting product metadata, and ambiguous repeated interaction IDs. Product
names/categories are required for the catalog. Missing prices remain null rather
than being guessed. The supplied data passes these checks without dropped rows.
Repeated user-product events, if introduced in a future source file, are retained
in the interaction output; the current file has none.

The model is appropriate for this explicit-feedback dataset:

- **Similar products:** user-centered item-rating cosine similarity, shrunk for
  small co-rating overlaps, blended 70/30 with TF-IDF cosine similarity from
  product name and category.
- **User recommendations:** ratings already recorded for a known user are
  compared with that user's mean rating and propagated through the item
  similarities. Already-rated products are excluded. The optional `max_price`
  filter restricts results to products at or below the requested INR budget.
- **Fallback:** Bayesian mean rating, shrunk toward the catalog-wide mean using
  a five-rating prior, is used when a useful personalized signal is unavailable.
- A selected item is excluded from its own similar-product list. Unknown IDs
  return HTTP 404. The dataset has no users without interaction history, so a
  new user's preference cannot be inferred; unknown users return 404 rather than
  being described as personalized.

There are no images or marketing descriptions in the source. Product similarity
should be understood as a small-dataset discovery signal, not semantic
understanding of product descriptions.

### Offline evaluation

Training uses one reproducibly seeded random interaction held out per user with
at least three interactions. Similarities and popularity priors are calculated
from the remaining training interactions only. A held-out rating of 4 or 5 is
the single relevant item for that user; users with a lower held-out rating are
not included in the relevant-user ranking metrics. The training command reports
Precision@5 and Recall@5 in `backend/artifacts/evaluation.json` and prints the
actual measured values to the terminal.

This is a small, single-split offline estimate—not a production performance
guarantee. One held-out item per user yields noisy metrics, and the synthetic or
otherwise undocumented source-generation process may not represent future user
behavior. No fabricated score is included here; run training on the supplied
file to regenerate the report. On the supplied 700-row file, the seeded run
produced 100 held-out interactions, 74 relevant held-out users, 5 hits in the
top five, **Precision@5 = 0.013514** and **Recall@5 = 0.067568**. These low
results are reported as measured; they indicate that this small dataset/model
combination has limited ranking quality and should not be presented as a
high-performing production recommender.

## API

Interactive Swagger UI is available at `http://localhost:8000/docs`.

| Method and route | Description |
|---|---|
| `GET /api/health` | Model and dataset counts |
| `GET /api/products?limit=20&offset=0&q=book&category=Books` | Search/filter catalog; `limit` 1–100 |
| `GET /api/products/{product_id}` | Catalog entry with computed rating summary |
| `GET /api/recommendations/product/{product_id}?limit=10` | Similar products; limit 1–20 |
| `GET /api/recommendations/user/{user_id}?limit=10&max_price=1000` | Recommendations for an observed user; optional INR budget; limit 1–20 |

Example:

```powershell
curl.exe "http://localhost:8000/api/recommendations/product/P001?limit=3"
```

Response shape:

```json
{
  "items": [
    {
      "product": {
        "product_id": "P005",
        "product_name": "Wireless Keyboard",
        "category": "Electronics",
        "price_inr": 1199.0,
        "average_rating": 4.053,
        "rating_count": 19
      },
      "score": 0.31,
      "reason": "Similar product and category"
    }
  ],
  "total": 1,
  "recommendation_type": "similar_products",
  "message": "Recommendations combine item-rating similarity with product name and category."
}
```

Scores are relative ranking scores, not calibrated probabilities. Invalid limits
receive HTTP 422; missing products/users receive HTTP 404.

## Run locally (Windows PowerShell)

Use Python 3.10 or newer and Node.js 18 or newer.

1. Install backend requirements:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Train, preprocess, and generate evaluation/model files (from `backend`):

   ```powershell
   python scripts\train.py
   ```

   If your CSV is elsewhere, pass its location explicitly:

   ```powershell
   python scripts\train.py --dataset "C:\path\to\product_recommendation_dataset_700.csv"
   ```

3. Start the API in the same activated environment:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

4. In a separate PowerShell window, start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Open `http://localhost:5173`. To use another API address, set
   `VITE_API_BASE_URL` before starting Vite, for example:

   ```powershell
   $env:VITE_API_BASE_URL = "http://localhost:8000"
   npm run dev
   ```

   For a different frontend origin, set `CORS_ORIGINS` to a comma-separated
   allowlist before starting the API.

## Tests and verification

From `backend` with the virtual environment active:

```powershell
python -m pytest
```

Test the health and recommendation endpoints in a browser or terminal, or use
the Swagger UI. In the frontend, the product list, details, and recommendations
are fetched from the API; stop the API to confirm that the interface displays a
connection error rather than showing hardcoded sample recommendations.

Build the frontend:

```powershell
cd frontend
npm install
npm run build
```

## Limitations and next steps

- The dataset provenance and license/usage terms were not supplied; verify them
  before publication or redistribution.
- The catalog is only 35 products and user histories are short (3–13 ratings).
- New users have no preference history; new products cannot have learned
  interaction similarity until rated.
- The offline split is intentionally simple; larger datasets should use
  repeated temporal splits and stronger ranking baselines.
- Product imagery, review text, inventory, and purchase data are unavailable.
#   D S - P r o j e c t  
 