import json
from pathlib import Path
from typing import Any


class Recommender:
    def __init__(self, artifact: dict[str, Any]) -> None:
        self.products: dict[str, dict[str, Any]] = artifact["products"]
        self.interactions: list[dict[str, Any]] = artifact["interactions"]
        self.similarities: dict[str, dict[str, float]] = artifact["similarities"]
        self.popularity: dict[str, float] = artifact["popularity"]
        self.user_ratings: dict[str, dict[str, float]] = artifact["user_ratings"]
        self.method = artifact["method"]

    @classmethod
    def load(cls, path: Path) -> "Recommender":
        if not path.is_file():
            raise FileNotFoundError(
                f"Model artifact not found at {path}. Run `python scripts/train.py` first."
            )
        with path.open(encoding="utf-8") as file:
            return cls(json.load(file))

    @property
    def interaction_count(self) -> int:
        return len(self.interactions)

    def product_details(self, product_id: str) -> dict[str, Any] | None:
        product = self.products.get(product_id)
        if product is None:
            return None
        return self._product_payload(product_id)

    def list_products(
        self, limit: int, offset: int, query: str | None = None, category: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        products = [self._product_payload(product_id) for product_id in self.products]
        if query:
            needle = query.casefold()
            products = [
                product
                for product in products
                if needle in product["product_name"].casefold()
                or needle in product["category"].casefold()
            ]
        if category:
            products = [
                product
                for product in products
                if product["category"].casefold() == category.casefold()
            ]
        products.sort(key=lambda product: product["product_id"])
        total = len(products)
        return products[offset : offset + limit], total

    def recommend_for_product(self, product_id: str, limit: int) -> list[dict[str, Any]]:
        if product_id not in self.products:
            return []
        candidates = [
            candidate_id
            for candidate_id in self.products
            if candidate_id != product_id
        ]
        candidates.sort(
            key=lambda candidate_id: (
                self.similarities.get(product_id, {}).get(candidate_id, 0.0),
                self.popularity.get(candidate_id, 0.0),
            ),
            reverse=True,
        )
        return [
            {
                "product": self._product_payload(candidate_id),
                "score": round(
                    self.similarities.get(product_id, {}).get(candidate_id, 0.0), 6
                ),
                "reason": "Similar product and category",
            }
            for candidate_id in candidates[:limit]
        ]

    def recommend_for_user(
        self, user_id: str, limit: int, max_price: float | None = None
    ) -> list[dict[str, Any]] | None:
        ratings = self.user_ratings.get(user_id)
        if ratings is None:
            return None

        unseen = [product_id for product_id in self.products if product_id not in ratings]
        if max_price is not None:
            unseen = [
                product_id
                for product_id in unseen
                if self.products[product_id]["price_inr"] is not None
                and self.products[product_id]["price_inr"] <= max_price
            ]
        if not unseen:
            return []

        user_mean = sum(ratings.values()) / len(ratings)
        scores: dict[str, float] = {}
        for candidate_id in unseen:
            weighted_preference = 0.0
            total_weight = 0.0
            for rated_id, rating in ratings.items():
                similarity = self.similarities.get(rated_id, {}).get(candidate_id, 0.0)
                if similarity > 0:
                    preference = (rating - user_mean) / 4
                    weighted_preference += similarity * preference
                    total_weight += similarity
            if total_weight > 0:
                # Blend the user's rating signal with the Bayesian popularity prior.
                preference_score = max(0.0, min(1.0, 0.5 + weighted_preference / total_weight))
                scores[candidate_id] = (
                    0.75 * preference_score + 0.25 * self.popularity[candidate_id]
                )
            else:
                scores[candidate_id] = self.popularity[candidate_id]

        has_personal_signal = any(
            rating > user_mean
            and self.similarities.get(rated_id, {}).get(candidate_id, 0.0) > 0
            for candidate_id in unseen
            for rated_id, rating in ratings.items()
        )
        recommendation_type = "personalized" if has_personal_signal else "popularity_fallback"
        reason = (
            "Based on products you rated"
            if recommendation_type == "personalized"
            else "Popular among all users (fallback)"
        )
        ranked = sorted(unseen, key=lambda candidate_id: scores[candidate_id], reverse=True)
        return [
            {
                "product": self._product_payload(candidate_id),
                "score": round(max(0.0, min(1.0, scores[candidate_id])), 6),
                "reason": reason,
                "recommendation_type": recommendation_type,
            }
            for candidate_id in ranked[:limit]
        ]

    def user_has_unseen_products(self, user_id: str) -> bool:
        ratings = self.user_ratings.get(user_id, {})
        return any(product_id not in ratings for product_id in self.products)

    def _product_payload(self, product_id: str) -> dict[str, Any]:
        return self.products[product_id]
