from typing import List
from ..entities.product import Product
from ..interfaces.parser_repository import ParserRepository

class SearchProductsUseCase:
    def __init__(self, parser_repository: ParserRepository):
        self.parser_repository = parser_repository

    async def execute(self, query: str, sort: str = "cheap", pages: int = 3) -> List[Product]:
        return await self.parser_repository.search_products(query, sort, pages)