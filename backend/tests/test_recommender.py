import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "backend" / "scripts"))

from app.services.recommender import Recommender
from train import load_and_clean, make_artifact


DATASET = ROOT_DIR / "product_recommendation_dataset_700.csv"


def build_recommender() -> Recommender:
    interactions, products, _ = load_and_clean(DATASET)
    return Recommender(make_artifact(interactions, products))


def test_product_recommendations_are_ranked_and_exclude_selected_product() -> None:
    recommender = build_recommender()

    recommendations = recommender.recommend_for_product("P001", 10)

    assert len(recommendations) == 10
    assert all(item["product"]["product_id"] != "P001" for item in recommendations)
    assert len({item["product"]["product_id"] for item in recommendations}) == 10
    assert all(0 <= item["score"] <= 1 for item in recommendations)


def test_user_recommendations_exclude_rated_products() -> None:
    recommender = build_recommender()
    rated = recommender.user_ratings["U001"]

    recommendations = recommender.recommend_for_user("U001", 10)

    assert recommendations is not None
    assert recommendations
    assert not rated.keys() & {
        item["product"]["product_id"] for item in recommendations
    }


def test_user_recommendations_respect_max_price() -> None:
    recommender = build_recommender()

    recommendations = recommender.recommend_for_user("U001", 20, max_price=500)

    assert recommendations is not None
    assert recommendations
    assert all(item["product"]["price_inr"] <= 500 for item in recommendations)
    assert not recommender.user_ratings["U001"].keys() & {
        item["product"]["product_id"] for item in recommendations
    }


def test_unknown_user_is_distinguished_from_user_with_empty_results() -> None:
    assert build_recommender().recommend_for_user("not-a-user", 10) is None


def test_catalog_search_filters_by_query_and_category() -> None:
    items, total = build_recommender().list_products(10, 0, "python", "Books")

    assert total == len(items)
    assert items
    assert all("python" in item["product_name"].casefold() for item in items)
    assert all(item["category"] == "Books" for item in items)


def test_data_loader_rejects_missing_schema(tmp_path: Path) -> None:
    dataset = tmp_path / "bad.csv"
    pd.DataFrame([{"product_id": "P1"}]).to_csv(dataset, index=False)

    try:
        load_and_clean(dataset)
    except ValueError as error:
        assert "missing required columns" in str(error)
    else:
        raise AssertionError("Expected required-column validation to fail")
