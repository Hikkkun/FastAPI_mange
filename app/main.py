import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

from app.api.v1.endpoints.manga.senkuro import router as senkuro_router
from app.api.v1.endpoints.ranobe.ranobe import router as ranobe_router
from app.redis.redis_client import init_redis, close_redis


logger = logging.getLogger(__name__) # Логгер для текущего модуля

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет жизненным циклом приложения: инициализирует и закрывает Redis.
    """
    logger.info("Инициализация Redis...")
    await init_redis()
    logger.info("Redis успешно инициализирован.")
    
    yield  # Приложение работает здесь
    
    logger.info("Закрытие Redis...")
    await close_redis()
    logger.info("Redis успешно закрыт.")
    

app = FastAPI(
    title="FastAPI Redis App",  # Название приложения
    version="1.0.0",  # Версия приложения
    lifespan=lifespan  # Управление жизненным циклом приложения
)

templates = Jinja2Templates(directory="app/templates")

# Подключение роутеров для работы с API
app.include_router(senkuro_router, tags=["Manga"])
app.include_router(ranobe_router, tags=["Ranobe"])

# Главная страница
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})