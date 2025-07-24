from dependency_injector import containers, providers
from .infrastructure.http_client.async_client import AsyncHTTPClient
from .infrastructure.cache.redis_cache import CacheService
from .infrastructure.parsers.wb_parser import WBParser
from .domain.use_cases.search_products import SearchProductsUseCase
from .domain.use_cases.search_products_by_link import SearchProductsByLinkUseCase
from .domain.use_cases.price_range import PriceRangeUseCase
from .domain.use_cases.fetch_feedbacks import FetchFeedbacksUseCase
from .domain.use_cases.fetch_products_by_supplier import FetchProductsBySupplierUseCase
from .domain.use_cases.fetch_ids_by_supplier import FetchIDsBySupplierUseCase

class AppContainer(containers.DeclarativeContainer):
    http_client = providers.Object(AsyncHTTPClient().get_client())
    cache_service = providers.Factory(CacheService)
    parser = providers.Factory(WBParser, http_client=http_client, cache_service=cache_service)
    search_use_case = providers.Factory(SearchProductsUseCase, parser_repository=parser)
    search_by_link_use_case = providers.Factory(SearchProductsByLinkUseCase, parser_repository=parser, search_use_case=search_use_case)
    price_range_use_case = providers.Factory(PriceRangeUseCase, parser_repository=parser)
    fetch_feedbacks_use_case = providers.Factory(FetchFeedbacksUseCase, parser_repository=parser)
    fetch_products_by_supplier_use_case = providers.Factory(FetchProductsBySupplierUseCase, parser_repository=parser)
    fetch_ids_by_supplier_use_case = providers.Factory(FetchIDsBySupplierUseCase, parser_repository=parser)