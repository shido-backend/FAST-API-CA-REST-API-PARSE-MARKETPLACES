from fastapi import Depends
from .container import AppContainer
from .domain.use_cases.search_products import SearchProductsUseCase
from .domain.use_cases.search_products_by_link import SearchProductsByLinkUseCase
from .domain.use_cases.price_range import PriceRangeUseCase
from .domain.use_cases.fetch_feedbacks import FetchFeedbacksUseCase
from .domain.use_cases.fetch_products_by_supplier import FetchProductsBySupplierUseCase
from .domain.use_cases.fetch_ids_by_supplier import FetchIDsBySupplierUseCase

container = AppContainer()

def get_search_use_case() -> SearchProductsUseCase:
    return container.search_use_case()

def get_search_by_link_use_case() -> SearchProductsByLinkUseCase:
    return container.search_by_link_use_case()

def get_price_range_use_case() -> PriceRangeUseCase:
    return container.price_range_use_case()

def get_fetch_feedbacks_use_case() -> FetchFeedbacksUseCase:
    return container.fetch_feedbacks_use_case()

def get_fetch_products_by_supplier_use_case() -> FetchProductsBySupplierUseCase:
    return container.fetch_products_by_supplier_use_case()

def get_fetch_ids_by_supplier_use_case() -> FetchIDsBySupplierUseCase:
    return container.fetch_ids_by_supplier_use_case()