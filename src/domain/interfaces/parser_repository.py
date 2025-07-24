from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from ..entities.product import Product, Feedback

class ParserRepository(ABC):
    @abstractmethod
    async def search_products(self, query: str, sort: str, pages: int) -> List[Product]:
        pass

    @abstractmethod
    async def get_product_by_link(self, link: str) -> Optional[Product]:
        pass

    @abstractmethod
    async def get_feedbacks(self, link: str) -> List[Feedback]:
        pass

    @abstractmethod
    async def get_products_by_supplier_id(self, supplier_id: int, pages: int) -> List[Product]:
        pass

    @abstractmethod
    async def get_supplier_ids_by_brand_url(self, brand_url: str) -> Optional[Tuple[int, int]]:
        pass