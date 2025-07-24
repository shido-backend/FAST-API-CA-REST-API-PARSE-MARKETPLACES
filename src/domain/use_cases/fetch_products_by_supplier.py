from typing import List
from ..entities.product import Product, ProductResponse
from ..interfaces.parser_repository import ParserRepository
import logging

logger = logging.getLogger(__name__)

class FetchProductsBySupplierUseCase:
    def __init__(self, parser_repository: ParserRepository):
        self.parser_repository = parser_repository

    async def execute(self, supplier_id: int, pages: int = 3) -> ProductResponse:
        logger.info(f"Processing products for supplier_id: {supplier_id}, pages: {pages}")
        products = await self.parser_repository.get_products_by_supplier_id(supplier_id, pages)
        return ProductResponse(count=len(products), products=products)