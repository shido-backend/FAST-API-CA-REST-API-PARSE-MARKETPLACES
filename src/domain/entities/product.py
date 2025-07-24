from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List
from datetime import datetime

class Product(BaseModel):
    id: int
    name: str
    price: float
    rating: Optional[float] = 0.0
    link: HttpUrl
    feedbacks: int = 0
    subjectId: int = 0
    root: Optional[int] = None

    class Config:
        json_encoders = {
            HttpUrl: str 
        }

class ProductResponse(BaseModel):
    count: int
    products: list[Product]

class PriceRangeResponse(BaseModel):
    query: str
    min_price: float
    max_price: float
    avg_price: float
    total_products: int
    price_distribution: Optional[Dict[str, int]] = None

class Feedback(BaseModel):
    id: str
    text: str
    pros: str
    cons: str
    rating: int
    created_date: datetime
    user_name: Optional[str] = None
    product_nm: int

class FeedbackResponse(BaseModel):
    count: int
    feedbacks: List[Feedback]