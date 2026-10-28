from pydantic import BaseModel, ConfigDict, Field


class Product(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: str
    product_name: str
    category: str
    price_inr: float | None = None
    average_rating: float
    rating_count: int


class ProductList(BaseModel):
    items: list[Product]
    total: int
    limit: int
    offset: int


class Recommendation(BaseModel):
    product: Product
    score: float = Field(ge=0, le=1)
    reason: str


class RecommendationList(BaseModel):
    items: list[Recommendation]
    total: int
    recommendation_type: str
    message: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    product_count: int
    interaction_count: int
    method: str
