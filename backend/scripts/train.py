import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "backend"))

REQUIRED_COLUMNS = {
    "interaction_id",
    "user_id",
    "product_id",
    "rating",
    "product_name",
    "category",
    "price_inr",
}


def load_and_clean(dataset_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    raw = pd.read_csv(dataset_path)
    missing_columns = REQUIRED_COLUMNS - set(raw.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

    diagnostics: dict[str, Any] = {
        "source_file": str(dataset_path),
        "input_rows": int(len(raw)),
        "columns": list(raw.columns),
        "input_dtypes": {column: str(dtype) for column, dtype in raw.dtypes.items()},
        "missing_values_by_column": {
            column: int(count) for column, count in raw.isna().sum().items()
        },
        "exact_duplicate_rows": int(raw.duplicated().sum()),
    }

    data = raw.drop_duplicates().copy()
    for column in ("interaction_id", "user_id", "product_id", "product_name", "category"):
        data[column] = data[column].fillna("").astype(str).str.strip()
    data["rating"] = pd.to_numeric(data["rating"], errors="coerce")
    data["price_inr"] = pd.to_numeric(data["price_inr"], errors="coerce")

    invalid_key_rows = (
        (data["interaction_id"] == "")
        | (data["user_id"] == "")
        | (data["product_id"] == "")
        | data["rating"].isna()
        | ~data["rating"].between(1, 5)
    )
    diagnostics["invalid_interaction_rows_dropped"] = int(invalid_key_rows.sum())
    data = data.loc[~invalid_key_rows].copy()
    if data["interaction_id"].duplicated().any():
        raise ValueError("Non-identical rows reuse an interaction_id; resolve this ambiguity.")

    if data["price_inr"].lt(0).any():
        raise ValueError("Negative product prices are not valid.")

    metadata_counts = data.groupby("product_id")[["product_name", "category"]].nunique()
    if (metadata_counts > 1).any().any():
        raise ValueError("A product_id maps to conflicting product names or categories.")
    price_counts = data.dropna(subset=["price_inr"]).groupby("product_id")["price_inr"].nunique()
    if (price_counts > 1).any():
        raise ValueError("A product_id maps to conflicting prices.")
    if (data["product_name"] == "").any() or (data["category"] == "").any():
        raise ValueError("Product names and categories are required to build the catalog.")

    diagnostics["clean_rows"] = int(len(data))
    diagnostics["clean_dtypes"] = {column: str(dtype) for column, dtype in data.dtypes.items()}
    diagnostics["duplicate_user_product_pairs"] = int(
        data.duplicated(subset=["user_id", "product_id"]).sum()
    )
    products = (
        data.groupby("product_id", sort=True)
        .agg(
            product_name=("product_name", "first"),
            category=("category", "first"),
            price_inr=("price_inr", "first"),
        )
        .reset_index()
    )
    diagnostics["user_count"] = int(data["user_id"].nunique())
    diagnostics["product_count"] = int(data["product_id"].nunique())
    diagnostics["rating_distribution"] = {
        str(key): int(value)
        for key, value in data["rating"].value_counts().sort_index().items()
    }
    return data, products, diagnostics


def make_artifact(interactions: pd.DataFrame, products: pd.DataFrame) -> dict[str, Any]:
    product_ids = products["product_id"].tolist()

    product_docs = (
        products["product_name"].astype(str) + " " + products["category"].astype(str)
    ).tolist()
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    content = vectorizer.fit_transform(product_docs)
    content_similarity = (content @ content.T).toarray()

    user_means = interactions.groupby("user_id")["rating"].mean().to_dict()
    ratings_by_product: dict[str, dict[str, float]] = defaultdict(dict)
    user_ratings: dict[str, dict[str, float]] = defaultdict(dict)
    for row in interactions.itertuples(index=False):
        user_id = str(row.user_id)
        product_id = str(row.product_id)
        rating = float(row.rating)
        ratings_by_product[product_id][user_id] = rating
        user_ratings[user_id][product_id] = rating

    popularity = {}
    global_mean = float(interactions["rating"].mean())
    for product_id in product_ids:
        values = list(ratings_by_product[product_id].values())
        # Five prior ratings shrink small-sample means toward the catalog average.
        popularity[product_id] = (
            sum(values) + 5 * global_mean
        ) / (len(values) + 5) / 5

    similarities: dict[str, dict[str, float]] = {}
    for left_index, left_id in enumerate(product_ids):
        similarities[left_id] = {}
        for right_index, right_id in enumerate(product_ids):
            if left_id == right_id:
                continue
            left = ratings_by_product[left_id]
            right = ratings_by_product[right_id]
            common_users = left.keys() & right.keys()
            collaborative = 0.0
            if len(common_users) >= 2:
                left_vector = np.array(
                    [left[user_id] - user_means[user_id] for user_id in common_users]
                )
                right_vector = np.array(
                    [right[user_id] - user_means[user_id] for user_id in common_users]
                )
                denominator = np.linalg.norm(left_vector) * np.linalg.norm(right_vector)
                if denominator > 0:
                    collaborative = float(np.dot(left_vector, right_vector) / denominator)
                collaborative = max(0.0, collaborative) * len(common_users) / (
                    len(common_users) + 5
                )

            content_score = float(content_similarity[left_index, right_index])
            similarities[left_id][right_id] = (
                0.7 * collaborative + 0.3 * content_score
            )

    catalog: dict[str, dict[str, Any]] = {}
    for row in products.itertuples(index=False):
        product_id = str(row.product_id)
        values = list(ratings_by_product[product_id].values())
        catalog[product_id] = {
            "product_id": product_id,
            "product_name": str(row.product_name),
            "category": str(row.category),
            "price_inr": None if pd.isna(row.price_inr) else float(row.price_inr),
            "average_rating": round(sum(values) / len(values), 3),
            "rating_count": len(values),
        }

    return {
        "method": "Hybrid item similarity: user-centered rating cosine with shrinkage (70%) and product-name/category TF-IDF cosine (30%); Bayesian rating popularity fallback.",
        "products": catalog,
        "interactions": [
            {
                "interaction_id": str(row.interaction_id),
                "user_id": str(row.user_id),
                "product_id": str(row.product_id),
                "rating": float(row.rating),
            }
            for row in interactions.itertuples(index=False)
        ],
        "user_ratings": {
            user_id: dict(ratings) for user_id, ratings in user_ratings.items()
        },
        "similarities": similarities,
        "popularity": popularity,
    }


def evaluate(interactions: pd.DataFrame, products: pd.DataFrame, k: int = 5) -> dict[str, Any]:
    rng = np.random.default_rng(42)
    heldout_indices = []
    for _, user_rows in interactions.groupby("user_id", sort=True):
        if len(user_rows) >= 3:
            heldout_indices.append(int(rng.choice(user_rows.index.to_numpy())))

    heldout = interactions.loc[heldout_indices]
    training = interactions.drop(index=heldout_indices)
    relevant = heldout.loc[heldout["rating"] >= 4]
    model = make_artifact(training, products)
    hits = 0
    users_with_relevant_item = 0
    for row in relevant.itertuples(index=False):
        user_id = str(row.user_id)
        heldout_product = str(row.product_id)
        user_ratings = model["user_ratings"].get(user_id, {})
        user_mean = sum(user_ratings.values()) / len(user_ratings)
        unseen = [product_id for product_id in model["products"] if product_id not in user_ratings]
        ranked = []
        for candidate_id in unseen:
            numerator = 0.0
            denominator = 0.0
            for rated_id, rating in user_ratings.items():
                similarity = model["similarities"][rated_id].get(candidate_id, 0.0)
                numerator += similarity * ((rating - user_mean) / 4)
                denominator += similarity
            preference = max(0.0, min(1.0, 0.5 + numerator / denominator)) if denominator else model["popularity"][candidate_id]
            score = (
                0.75 * preference + 0.25 * model["popularity"][candidate_id]
                if denominator
                else preference
            )
            ranked.append((candidate_id, score))
        ranked.sort(key=lambda item: item[1], reverse=True)
        if any(product_id == heldout_product for product_id, _ in ranked[:k]):
            hits += 1
        users_with_relevant_item += 1

    precision = hits / (users_with_relevant_item * k) if users_with_relevant_item else 0.0
    recall = hits / users_with_relevant_item if users_with_relevant_item else 0.0
    return {
        "protocol": (
            "One seeded random interaction held out per user (users with at least 3 records); "
            "training-only similarities/popularity; held-out ratings >= 4 count as relevant."
        ),
        "random_seed": 42,
        "k": k,
        "heldout_interactions": len(heldout),
        "relevant_heldout_users": users_with_relevant_item,
        f"precision_at_{k}": round(precision, 6),
        f"recall_at_{k}": round(recall, 6),
        "hits": hits,
    }


def train(
    dataset_path: Path,
    artifact_path: Path,
    processed_dir: Path,
    evaluation_path: Path,
) -> dict[str, Any]:
    interactions, products, diagnostics = load_and_clean(dataset_path)
    artifact = make_artifact(interactions, products)
    evaluation = evaluate(interactions, products)

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    evaluation_path.parent.mkdir(parents=True, exist_ok=True)
    interactions.to_csv(processed_dir / "interactions.csv", index=False)
    products.to_csv(processed_dir / "products.csv", index=False)
    with artifact_path.open("w", encoding="utf-8") as file:
        json.dump(artifact, file, ensure_ascii=False, separators=(",", ":"))
    report = {"data_quality": diagnostics, "evaluation": evaluation}
    with evaluation_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean, train, and evaluate the recommender.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT_DIR / "product_recommendation_dataset_700.csv",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT_DIR / "backend" / "artifacts" / "recommender.json",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=ROOT_DIR / "backend" / "data" / "processed",
    )
    parser.add_argument(
        "--evaluation",
        type=Path,
        default=ROOT_DIR / "backend" / "artifacts" / "evaluation.json",
    )
    args = parser.parse_args()
    report = train(args.dataset, args.artifact, args.processed_dir, args.evaluation)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
