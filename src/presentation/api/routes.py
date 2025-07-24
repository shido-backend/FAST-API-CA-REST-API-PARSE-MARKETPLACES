from fastapi import APIRouter, Query, Depends
from ...domain.entities.product import ProductResponse, PriceRangeResponse, FeedbackResponse
from ...domain.use_cases.search_products import SearchProductsUseCase
from ...domain.use_cases.search_products_by_link import SearchProductsByLinkUseCase
from ...domain.use_cases.price_range import PriceRangeUseCase
from ...domain.use_cases.fetch_feedbacks import FetchFeedbacksUseCase
from ...domain.use_cases.fetch_products_by_supplier import FetchProductsBySupplierUseCase
from ...domain.use_cases.fetch_ids_by_supplier import FetchIDsBySupplierUseCase
from ...dependencies import get_search_use_case, get_search_by_link_use_case, get_price_range_use_case, get_fetch_feedbacks_use_case, get_fetch_products_by_supplier_use_case, get_fetch_ids_by_supplier_use_case
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/search", response_model=ProductResponse)
async def search_products(
    query: str = Query(..., description="Поисковый запрос"),
    sort: str = Query("cheap", description="Сортировка: 'cheap' или 'expensive'"),
    pages: int = Query(3, description="Количество страниц для анализа"),
    use_case: SearchProductsUseCase = Depends(get_search_use_case)
):
    logger.info(f"Processing search query: {query}, sort: {sort}, pages: {pages}")
    products = await use_case.execute(query, sort, pages)
    return ProductResponse(count=len(products), products=products)

@router.get("/top_products", response_model=dict)
async def top_products(
    query: str = Query(..., description="Поисковый запрос"),
    pages: int = Query(3, description="Количество страниц для анализа"),
    use_case: SearchProductsUseCase = Depends(get_search_use_case)
):
    logger.info(f"Processing top products query: {query}, pages: {pages}")
    expensive_products = await use_case.execute(query, "expensive", pages)
    cheap_products = await use_case.execute(query, "cheap", pages)

    top_expensive = sorted(expensive_products, key=lambda x: x.rating, reverse=True)[:3]
    top_cheap = sorted(cheap_products, key=lambda x: x.rating, reverse=True)[:3]

    return {
        "top_expensive": top_expensive,
        "top_cheap": top_cheap
    }

@router.get("/product_by_link", response_model=dict)
async def product_by_link(
    link: str = Query(..., description="Ссылка на товар Wildberries"),
    pages: int = Query(3, description="Количество страниц для поиска аналогов"),
    use_case: SearchProductsByLinkUseCase = Depends(get_search_by_link_use_case)
):
    logger.info(f"Processing product by link: {link}, pages: {pages}")
    result = await use_case.execute(link, pages)
    return result

@router.get("/price_range", response_model=PriceRangeResponse)
async def price_range(
    query: str = Query(..., description="Поисковый запрос"),
    pages: int = Query(3, description="Количество страниц для анализа"),
    use_case: PriceRangeUseCase = Depends(get_price_range_use_case)
):
    logger.info(f"Processing price range query: {query}, pages: {pages}")
    return await use_case.execute(query, pages)

@router.get("/feedbacks", response_model=FeedbackResponse)
async def get_feedbacks(
    link: str = Query(..., description="Ссылка на товар Wildberries"),
    use_case: FetchFeedbacksUseCase = Depends(get_fetch_feedbacks_use_case)
):
    logger.info(f"Processing feedbacks for link: {link}")
    return await use_case.execute(link)

@router.get("/products_by_supplier", response_model=ProductResponse)
async def get_products_by_supplier(
    supplier_id: int = Query(..., description="ID продавца"),
    pages: int = Query(3, description="Количество страниц для анализа"),
    use_case: FetchProductsBySupplierUseCase = Depends(get_fetch_products_by_supplier_use_case)
):
    logger.info(f"Processing products for supplier_id: {supplier_id}, pages: {pages}")
    return await use_case.execute(supplier_id, pages)

@router.get("/supplier_ids_by_brand", response_model=dict)
async def get_supplier_ids_by_brand(
    brand_url: str = Query(..., description="Ссылка на бренд Wildberries"),
    use_case: FetchIDsBySupplierUseCase = Depends(get_fetch_ids_by_supplier_use_case)
):
    logger.info(f"Processing supplier IDs for brand URL: {brand_url}")
    return await use_case.execute(brand_url)