from typing import Dict, List, Optional
from ..entities.product import Product, PriceRangeResponse
from ..interfaces.parser_repository import ParserRepository
from statistics import mean
import logging

logger = logging.getLogger(__name__)

def calculate_price_distribution(prices: List[float]) -> Dict[str, int]:
    max_price = max(prices)
    step = (max_price + 100) / 5
    distribution = {f"{i*step:.0f}-{(i+1)*step:.0f}": 0 for i in range(5)}

    for price in prices:
        for i in range(5):
            if i * step <= price < (i + 1) * step:
                distribution[f"{i*step:.0f}-{(i+1)*step:.0f}"] += 1
                break

    return distribution

class PriceRangeUseCase:
    def __init__(self, parser_repository: ParserRepository):
        self.parser_repository = parser_repository

    async def execute(self, query: str, pages: int = 3) -> PriceRangeResponse:
        logger.info(f"Processing price range query: {query}, pages: {pages}")
        products = await self.parser_repository.search_products(query, sort="cheap", pages=pages)

        if not products:
            return PriceRangeResponse(
                query=query,
                min_price=0.0,
                max_price=0.0,
                avg_price=0.0,
                total_products=0
            )

        prices = [product.price for product in products]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = mean(prices)

        price_distribution = None
        if prices:
            price_distribution = calculate_price_distribution(prices)

        return PriceRangeResponse(
            query=query,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            total_products=len(products),
            price_distribution=price_distribution
        )