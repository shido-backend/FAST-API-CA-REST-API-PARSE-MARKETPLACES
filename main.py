from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from src.container import AppContainer
from src.dependencies import get_search_use_case, get_search_by_link_use_case
from src.presentation.api.routes import router
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
app = FastAPI(
    title="Wildberries API",
    description="API для парсинга данных с Wildberries",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)