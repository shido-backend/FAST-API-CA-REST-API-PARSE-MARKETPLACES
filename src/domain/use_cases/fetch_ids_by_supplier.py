from typing import List
from ..entities.product import Feedback, FeedbackResponse
from ..interfaces.parser_repository import ParserRepository
import logging

logger = logging.getLogger(__name__)

class FetchIDsBySupplierUseCase:
    def __init__(self, parser_repository: ParserRepository):
        self.parser_repository = parser_repository

    async def execute(self, brand_url: str) -> FeedbackResponse:
        logger.info(f"Processing ids for link: {brand_url}")
        supplier_id, site_id = await self.parser_repository.get_supplier_ids_by_brand_url(brand_url)
        return {"supplier_id": supplier_id, "site_id": site_id}