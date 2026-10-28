import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR / "backend" / "scripts"))

from app.main import create_app
from app.services.recommender import Recommender
from train import load_and_clean, make_artifact


def client() -> TestClient:
    interactions, products, _ = load_and_clean(
        ROOT_DIR / "product_recommendation_dataset_700.csv"
    )
    recommender = Recommender(make_artifact(interactions, products))
    return TestClient(create_app(recommender))


def test_health_and_product_endpoint() -> None:
    with client() as test_client:
        health = test_client.get("/api/health")
        product = test_client.get("/api/products/P001")

    assert health.status_code == 200
    assert health.json()["product_count"] == 35
    assert product.status_code == 200
    assert product.json()["product_name"] == "Wireless Mouse"


def test_unknown_product_and_user_return_404() -> None:
    with client() as test_client:
        unknown_product = test_client.get("/api/products/unknown")
        unknown_user = test_client.get("/api/recommendations/user/unknown")

    assert unknown_product.status_code == 404
    assert unknown_user.status_code == 404


def test_recommendation_endpoints_return_actual_catalog_items() -> None:
    with client() as test_client:
        product_response = test_client.get(
            "/api/recommendations/product/P001?limit=5"
        )
        user_response = test_client.get("/api/recommendations/user/U001?limit=5")

    assert product_response.status_code == 200
    assert len(product_response.json()["items"]) == 5
    assert all(
        item["product"]["product_id"] != "P001"
        for item in product_response.json()["items"]
    )
    assert user_response.status_code == 200
    assert len(user_response.json()["items"]) == 5


def test_user_recommendations_apply_max_price_and_handle_empty_budget() -> None:
    with client() as test_client:
        affordable = test_client.get(
            "/api/recommendations/user/U001?limit=20&max_price=500"
        )
        no_matches = test_client.get(
            "/api/recommendations/user/U001?limit=6&max_price=0"
        )

    assert affordable.status_code == 200
    assert affordable.json()["items"]
    assert all(
        item["product"]["price_inr"] <= 500
        for item in affordable.json()["items"]
    )
    assert no_matches.status_code == 200
    assert no_matches.json()["items"] == []
    assert no_matches.json()["recommendation_type"] == "no_products_under_budget"


def test_invalid_limit_is_rejected() -> None:
    with client() as test_client:
        response = test_client.get("/api/recommendations/product/P001?limit=21")

    assert response.status_code == 422


def test_negative_max_price_is_rejected() -> None:
    with client() as test_client:
        response = test_client.get(
            "/api/recommendations/user/U001?max_price=-1"
        )

    assert response.status_code == 422
