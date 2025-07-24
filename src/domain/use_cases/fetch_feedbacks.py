from typing import List
from ..entities.product import Feedback, FeedbackResponse
from ..interfaces.parser_repository import ParserRepository
import logging

logger = logging.getLogger(__name__)

class FetchFeedbacksUseCase:
    def __init__(self, parser_repository: ParserRepository):
        self.parser_repository = parser_repository

    async def execute(self, link: str) -> FeedbackResponse:
        logger.info(f"Processing feedbacks for link: {link}")
        feedbacks = await self.parser_repository.get_feedbacks(link)
        return FeedbackResponse(count=len(feedbacks), feedbacks=feedbacks)