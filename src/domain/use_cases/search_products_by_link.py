from typing import Dict, List
from ..entities.product import Product
from ..interfaces.parser_repository import ParserRepository
from .search_products import SearchProductsUseCase
import logging
import time

logger = logging.getLogger(__name__)

class SearchProductsByLinkUseCase:
    def __init__(self, parser_repository: ParserRepository, search_use_case: SearchProductsUseCase):
        self.parser_repository = parser_repository
        self.search_use_case = search_use_case

    async def execute(self, link: str, pages: int = 3) -> Dict[str, List[Product]]:
        start_time = time.time()
        try:
            product = await self.parser_repository.get_product_by_link(link)
        except Exception as e:
            logger.error(f"Failed to fetch product by link {link}: {e}")
            raise ValueError(f"Failed to fetch product: {str(e)}")

        logger.info(f"Fetched product by link {link}, time: {time.time() - start_time:.2f}s")

        cheap_products = await self.search_use_case.execute(product.name, sort="cheap", pages=pages)
        expensive_products = await self.search_use_case.execute(product.name, sort="expensive", pages=pages)
        logger.info(f"Searched products for {product.name}, time: {time.time() - start_time:.2f}s")

        all_products = list({p.id: p for p in cheap_products + expensive_products}.values())

        min_price_threshold = product.price * 0.1  
        min_feedbacks = 0

        better_price = [
            p for p in all_products
            if p.price <= product.price
            and p.price >= min_price_threshold
            and p.feedbacks >= min_feedbacks
            and p.subjectId == product.subjectId
            and p.id != product.id
        ]
        better_rating = [
            p for p in all_products
            if p.rating >= product.rating
            and p.price >= min_price_threshold
            and p.feedbacks >= min_feedbacks
            and p.subjectId == product.subjectId
            and p.id != product.id
        ]
        better_price = sorted(better_price, key=lambda x: x.price)[:3]
        better_rating = sorted(better_rating, key=lambda x: x.rating, reverse=True)[:3]

        logger.info(f"Processed results for link {link}, time: {time.time() - start_time:.2f}s")
        return {
            "original_product": product,
            "better_price": better_price,
            "better_rating": better_rating
        }