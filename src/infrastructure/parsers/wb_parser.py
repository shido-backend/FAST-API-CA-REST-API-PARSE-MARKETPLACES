import httpx
from typing import List, Optional, Tuple
from ...domain.entities.product import Product, Feedback
from ...domain.interfaces.parser_repository import ParserRepository
from ...exceptions.custom_exceptions import ParserError
from ...config.settings import get_settings
from ..cache.redis_cache import CacheService
import logging
import hashlib
import re
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class WBParser(ParserRepository):
    def __init__(self, http_client: httpx.AsyncClient, cache_service: CacheService):
        self.settings = get_settings()
        self.http_client = http_client
        self.cache_service = cache_service

    async def search_products(self, query: str, sort: str, pages: int) -> List[Product]:
        cache_key = self._generate_cache_key(query, sort, pages)
        cached_products = await self.cache_service.get(cache_key)
        
        if cached_products:
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_products

        sort_param = "priceup" if sort == "cheap" else "pricedown"
        all_products = []
        max_pages = min(pages, self.settings.max_pages)

        semaphore = asyncio.Semaphore(10) 

        async def fetch_page_with_semaphore(page: int) -> Optional[List[Product]]:
            async with semaphore:
                try:
                    products = await self._fetch_page(query, sort_param, page)
                    logger.info(f"Fetched {len(products)} products for query {query}, page {page}")
                    return products
                except ParserError as e:
                    logger.error(f"Failed to fetch page {page}: {e}")
                    return []

        for batch_start in range(1, max_pages + 1, 10):
            batch_end = min(batch_start + 9, max_pages + 1)
            tasks = [
                asyncio.ensure_future(fetch_page_with_semaphore(page))
                for page in range(batch_start, batch_end)
            ]
            completed, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in completed:
                page = batch_start + tasks.index(task)
                result = task.result()
                if isinstance(result, list):
                    if not result:
                        logger.info(f"Empty page {page} for query {query}, stopping further parsing")
                        for pending_task in pending:
                            pending_task.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        sorted_products = sorted(all_products, key=lambda x: x.rating, reverse=True)
                        await self.cache_service.set(cache_key, sorted_products, self.settings.cache_ttl)
                        logger.info(f"Cache set successfully for key: {cache_key}")
                        return sorted_products
                    all_products.extend(result)
                else:
                    logger.error(f"Error in page {page} fetch: {result}")
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        sorted_products = sorted(all_products, key=lambda x: x.rating, reverse=True)
        await self.cache_service.set(cache_key, sorted_products, self.settings.cache_ttl)
        logger.info(f"Cache set successfully for key: {cache_key}")
        return sorted_products

    async def get_product_by_link(self, link: str) -> Optional[Product]:
        cache_key = self._generate_cache_key_for_link(link)
        cached_product = await self.cache_service.get(cache_key, model=Product)
        
        if cached_product and len(cached_product) > 0:
            logger.info(f"Cache hit for key: {cache_key}")
            if not cached_product[0].root:
                logger.warning(f"Cached product for {link} has no root, clearing cache")
                await self.cache_service.client.delete(cache_key)
            else:
                return cached_product[0]
        logger.info(f"Cache miss for key: {cache_key}")

        product_id = self._extract_product_id(link)
        if not product_id:
            logger.error(f"Invalid product link: {link}")
            raise ParserError(f"Invalid product link: {link}")

        try:
            params = {
                "appType": "1",
                "curr": self.settings.default_currency,
                "dest": self.settings.default_destination,
                "spp": "30",
                "hide_dtype": "13;14",
                "ab_testing": "false",
                "lang": "ru",
                "nm": product_id
            }
            url = "https://card.wb.ru/cards/v4/detail"
            logger.info(f"Sending request to {url} with params: {params}")
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            response_json = response.json()
            logger.debug(f"API response for link {link}: {response_json}")
            products = self._parse_products(response_json)

            if not products:
                logger.error(f"No product found for link: {link}, response: {response_json}")
                raise ParserError(f"No product found for link: {link}")

            product = products[0]
            if not product.root:
                logger.error(f"No root field in product data for link: {link}")
                raise ParserError(f"No product_nm found for link: {link}")
            
            await self.cache_service.set(cache_key, [product], self.settings.cache_ttl)
            logger.info(f"Cache set successfully for key: {cache_key}")
            return product

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for link {link}: {e}, status: {e.response.status_code}")
            raise ParserError(f"Failed to fetch product: {e}")
        except Exception as e:
            logger.error(f"Parsing error for link {link}: {e}")
            raise ParserError(f"Failed to parse product: {e}")

    async def get_feedbacks(self, link: str) -> List[Feedback]:
        product = await self.get_product_by_link(link)
        if not product or not product.root:
            logger.error(f"Failed to extract product_nm from link: {link}")
            raise ParserError(f"Failed to extract product_nm from link: {link}")

        product_nm = product.root
        cache_key = self._generate_cache_key_for_feedbacks(product_nm)
        cached_feedbacks = await self.cache_service.get(cache_key, model=Feedback)
        
        if cached_feedbacks:
            logger.info(f"Cache hit for feedback key: {cache_key}")
            return cached_feedbacks

        all_feedbacks = []
        page = 1
        max_pages = 100  

        try:
            while True:
                url = f"https://feedbacks2.wb.ru/feedbacks/v2/{product_nm}?page={page}"
                logger.info(f"Sending request to {url}")
                response = await self.http_client.get(url)
                response.raise_for_status()
                response_json = response.json()
                logger.debug(f"API response for feedbacks product_nm {product_nm}, page {page}: {response_json}")

                feedbacks = self._parse_feedbacks(response_json, product_nm)
                if not feedbacks:
                    logger.info(f"No more feedbacks found for product_nm {product_nm} on page {page}")
                    break

                all_feedbacks.extend(feedbacks)
                page += 1

                feedback_count = response_json.get("feedbackCount", 0)
                if len(all_feedbacks) >= feedback_count or page > max_pages:
                    break

            if not all_feedbacks:
                logger.info(f"No feedbacks found for product_nm: {product_nm}")
                return []

            await self.cache_service.set(cache_key, all_feedbacks, self.settings.cache_ttl)
            logger.info(f"Cache set successfully for feedback key: {cache_key}")
            return all_feedbacks

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for feedbacks product_nm {product_nm}: {e}, status: {e.response.status_code}")
            raise ParserError(f"Failed to fetch feedbacks: {e}")
        except Exception as e:
            logger.error(f"Parsing error for feedbacks product_nm {product_nm}: {e}")
            raise ParserError(f"Failed to parse feedbacks: {e}")

    async def get_products_by_supplier_id(self, supplier_id: int, pages: int) -> List[Product]:
        cache_key = self._generate_cache_key_for_supplier(supplier_id, pages)
        cached_products = await self.cache_service.get(cache_key)
        
        if cached_products:
            logger.info(f"Cache hit for key: {cache_key}")
            return cached_products

        all_products = []
        max_pages = min(pages, self.settings.max_pages)

        semaphore = asyncio.Semaphore(5)

        async def fetch_page_with_semaphore(page: int) -> Optional[List[Product]]:
            async with semaphore:
                retries = 30
                last_exception = None
                
                for attempt in range(retries):
                    try:
                        products = await self._fetch_supplier_page(supplier_id, page)
                        logger.info(f"Fetched {len(products)} products for supplier {supplier_id}, page {page}")
                        await asyncio.sleep(0.6)  
                        return products
                    except ParserError as e:
                        last_exception = e
                        logger.warning(f"Attempt {attempt + 1} failed for page {page}: {e}")
                        if attempt < retries - 1:
                            await asyncio.sleep(0.6 * (attempt + 1))
                        continue
                
                logger.error(f"All retries failed for supplier page {page}: {last_exception}")
                return []

        for batch_start in range(1, max_pages + 1, 10):
            batch_end = min(batch_start + 9, max_pages + 1)
            tasks = [
                asyncio.ensure_future(fetch_page_with_semaphore(page))
                for page in range(batch_start, batch_end)
            ]
            completed, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in completed:
                page = batch_start + tasks.index(task)
                result = task.result()
                if isinstance(result, list):
                    if not result:
                        logger.info(f"Empty page {page} for supplier {supplier_id}, stopping further parsing")
                        for pending_task in pending:
                            pending_task.cancel()
                        await asyncio.gather(*pending, return_exceptions=True)
                        sorted_products = sorted(all_products, key=lambda x: x.rating, reverse=True)
                        await self.cache_service.set(cache_key, sorted_products, self.settings.cache_ttl)
                        logger.info(f"Cache set successfully for supplier key: {cache_key}")
                        return sorted_products
                    all_products.extend(result)
                else:
                    logger.error(f"Error in supplier page {page} fetch: {result}")
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        sorted_products = sorted(all_products, key=lambda x: x.rating, reverse=True)
        await self.cache_service.set(cache_key, sorted_products, self.settings.cache_ttl)
        logger.info(f"Cache set successfully for supplier key: {cache_key}")
        return sorted_products

    async def get_supplier_ids_by_brand_url(self, brand_url: str) -> Optional[Tuple[int, int]]:
        brand_name = self._extract_brand_name(brand_url)
        if not brand_name:
            logger.error(f"Invalid brand URL: {brand_url}")
            raise ParserError(f"Invalid brand URL: {brand_url}")

        #cache_key = self._generate_cache_key_for_brand(brand_name)
        #cached_data = await self.cache_service.get(cache_key)
        
        #if cached_data:
        #    logger.info(f"Cache hit for brand key: {cache_key}")
        #    return (cached_data[0]["id"], cached_data[0]["siteId"])

        try:
            url = f"https://static-basket-01.wbbasket.ru/vol0/data/brands/{brand_name}.json"
            logger.info(f"Sending request to {url}")
            response = await self.http_client.get(url)
            response.raise_for_status()
            response_json = response.json()
            logger.debug(f"API response for brand {brand_name}: {response_json}")

            supplier_id = response_json.get("id")
            site_id = response_json.get("siteId")
            if not supplier_id or not site_id:
                logger.error(f"No supplier ID or site ID found for brand: {brand_name}")
                raise ParserError(f"No supplier ID or site ID found for brand: {brand_name}")

            #await self.cache_service.set(cache_key, [{"id": supplier_id, "siteId": site_id}], self.settings.cache_ttl)
            #logger.info(f"Cache set successfully for brand key: {cache_key}")
            return (supplier_id, site_id)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for brand {brand_name}: {e}, status: {e.response.status_code}")
            raise ParserError(f"Failed to fetch brand data: {e}")
        except Exception as e:
            logger.error(f"Parsing error for brand {brand_name}: {e}")
            raise ParserError(f"Failed to parse brand data: {e}")

    def _generate_cache_key(self, query: str, sort: str, pages: int) -> str:
        key = f"wb:search:{query}:{sort}:{pages}"
        return hashlib.md5(key.encode()).hexdigest()

    def _generate_cache_key_for_link(self, link: str) -> str:
        key = f"wb:product:{link}"
        return hashlib.md5(key.encode()).hexdigest()

    def _generate_cache_key_for_feedbacks(self, product_nm: int) -> str:
        key = f"wb:feedbacks:{product_nm}"
        return hashlib.md5(key.encode()).hexdigest()

    def _generate_cache_key_for_supplier(self, supplier_id: int, pages: int) -> str:
        key = f"wb:supplier:{supplier_id}:{pages}"
        return hashlib.md5(key.encode()).hexdigest()

    def _generate_cache_key_for_brand(self, brand_name: str) -> str:
        key = f"wb:brand:{brand_name}"
        return hashlib.md5(key.encode()).hexdigest()

    def _extract_product_id(self, link: str) -> Optional[str]:
        match = re.search(r"/catalog/(\d+)/detail\.aspx", link)
        return match.group(1) if match else None

    def _extract_brand_name(self, brand_url: str) -> Optional[str]:
        match = re.search(r"/brands/([^/]+)/all", brand_url)
        return match.group(1) if match else None

    async def _fetch_page(self, query: str, sort: str, page: int) -> Optional[List[Product]]:
        try:
            params = {
                "query": query,
                "page": page,
                "sort": sort,
                "curr": self.settings.default_currency,
                "spp": "100",
                "dest": self.settings.default_destination,
                "hide_dtype": "10",
                "appType": "1",
                "lang": "ru",
                "resultset": "catalog",
                "suppressSpellcheck": "false"
            }
            response = await self.http_client.get(self.settings.wb_base_url, params=params)
            response.raise_for_status()
            response_json = response.json()
            logger.debug(f"API response for search query {query}, page {page}: {response_json}")
            return self._parse_products(response_json)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error on page {page}: {e}")
            raise ParserError(f"Failed to fetch page {page}: {e}")
        except Exception as e:
            logger.error(f"Parsing error on page {page}: {e}")
            raise ParserError(f"Failed to parse page {page}: {e}")

    async def _fetch_supplier_page(self, supplier_id: int, page: int) -> Optional[List[Product]]:
        try:
            params = {
                "appType": "1",
                "brand": supplier_id,
                "curr": self.settings.default_currency,
                "dest": self.settings.default_destination,
                "spp": "30",
                "hide_dtype": "13;14",
                "ab_testing": "false",
                "lang": "ru",
                "page": page,
                "sort": "popular"
            }
            url = "https://catalog.wb.ru/brands/v4/catalog"
            logger.info(f"Sending request to {url} with params: {params}")
            response = await self.http_client.get(url, params=params)
            response.raise_for_status()
            response_json = response.json()
            logger.debug(f"API response for supplier {supplier_id}, page {page}: {response_json}")
            return self._parse_products(response_json)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for supplier {supplier_id}, page {page}: {e}")
            raise ParserError(f"Failed to fetch supplier page {page}: {e}")
        except Exception as e:
            logger.error(f"Parsing error for supplier {supplier_id}, page {page}: {e}")
            raise ParserError(f"Failed to parse supplier page {page}: {e}")

    def _parse_products(self, data: dict) -> List[Product]:
        products = []
        data_products = data.get("products", data.get("data", {}).get("products", []))
        if not isinstance(data_products, list):
            logger.error(f"Unexpected products format: {data_products}")
            return products

        for item in data_products:
            price_data = item.get("sizes", [{}])[0].get("price", {})
            price = price_data.get("product", price_data.get("total", 0)) / 100
            product_id = item.get("id")
            if not product_id:
                logger.warning(f"Skipping item without id: {item}")
                continue
            product_nm = item.get("root", product_id)
            product_link = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

            products.append(Product(
                id=product_id,
                name=item.get("name", "Unknown"),
                price=price,
                rating=item.get("reviewRating", item.get("nmReviewRating", item.get("rating", 0.0))),
                link=product_link,
                feedbacks=item.get("feedbacks", 0),
                subjectId=item.get("subjectId", 0),
                root=product_nm
            ))
        return products

    def _parse_feedbacks(self, data: dict, product_nm: int) -> List[Feedback]:
        feedbacks = []
        feedback_data = data.get("feedbacks", [])
        if not isinstance(feedback_data, list):
            logger.error(f"Unexpected feedbacks format: {feedback_data}")
            return feedbacks

        for item in feedback_data:
            feedback_id = item.get("id")
            if not feedback_id:
                logger.warning(f"Skipping feedback without id: {item}")
                continue

            feedbacks.append(Feedback(
                id=feedback_id,
                text=item.get("text", ""),
                pros=item.get("pros", ""),
                cons=item.get("cons", ""),
                rating=item.get("productValuation", 0),
                created_date=datetime.fromisoformat(item.get("createdDate", "1970-01-01T00:00:00Z")),
                user_name=item.get("wbUserDetails", {}).get("name"),
                product_nm=product_nm
            ))
        return feedbacks