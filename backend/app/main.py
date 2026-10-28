import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    HealthResponse,
    Product,
    ProductList,
    RecommendationList,
)
from app.services.recommender import Recommender

ROOT_DIR = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = Path(
    os.getenv(
        "MODEL_ARTIFACT_PATH",
        str(ROOT_DIR / "backend" / "artifacts" / "recommender.json"),
    )
)
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def create_app(recommender: Recommender | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if recommender is not None:
            app.state.recommender = recommender
        else:
            app.state.recommender = Recommender.load(ARTIFACT_PATH)
        yield

    app = FastAPI(
        title="Product Recommendation System",
        description="Product discovery powered by rating-based and content-based recommendations.",
        version="1.0.0",
        lifespan=lifespan,
    )
    origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        model = request.app.state.recommender
        return HealthResponse(
            status="ok",
            model_loaded=True,
            product_count=len(model.products),
            interaction_count=model.interaction_count,
            method=model.method,
        )

    @app.get("/api/products", response_model=ProductList)
    def products(
        request: Request,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        q: str | None = Query(default=None, max_length=100),
        category: str | None = Query(default=None, max_length=80),
    ) -> ProductList:
        items, total = request.app.state.recommender.list_products(
            limit, offset, q, category
        )
        return ProductList(items=items, total=total, limit=limit, offset=offset)

    @app.get("/api/products/{product_id}", response_model=Product)
    def product(product_id: str, request: Request) -> Product:
        result = request.app.state.recommender.product_details(product_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return Product(**result)

    @app.get(
        "/api/recommendations/product/{product_id}",
        response_model=RecommendationList,
    )
    def product_recommendations(
        product_id: str,
        request: Request,
        limit: int = Query(default=10, ge=1, le=20),
    ) -> RecommendationList:
        model = request.app.state.recommender
        if model.product_details(product_id) is None:
            raise HTTPException(status_code=404, detail="Product not found")
        items = model.recommend_for_product(product_id, limit)
        return RecommendationList(
            items=items,
            total=len(items),
            recommendation_type="similar_products",
            message="Recommendations combine item-rating similarity with product name and category.",
        )

    @app.get(
        "/api/recommendations/user/{user_id}",
        response_model=RecommendationList,
    )
    def user_recommendations(
        user_id: str,
        request: Request,
        limit: int = Query(default=10, ge=1, le=20),
        max_price: float | None = Query(default=None, ge=0, le=1_000_000),
    ) -> RecommendationList:
        model = request.app.state.recommender
        items = model.recommend_for_user(user_id, limit, max_price)
        if items is None:
            raise HTTPException(status_code=404, detail="User not found in interaction data")
        recommendation_type = (
            items[0]["recommendation_type"] if items else "no_unseen_products"
        )
        if (
            not items
            and max_price is not None
            and model.user_has_unseen_products(user_id)
        ):
            recommendation_type = "no_products_under_budget"
        return RecommendationList(
            items=items,
            total=len(items),
            recommendation_type=recommendation_type,
            message=(
                "Based on this user's recorded ratings."
                if recommendation_type == "personalized"
                else "No rating-based signal was available; showing the popularity fallback."
                if recommendation_type == "popularity_fallback"
                else f"No unrated products are available at or below ₹{max_price:,.0f}."
                if recommendation_type == "no_products_under_budget"
                else "This user has already rated every product."
            ),
        )

    return app


app = create_app()
