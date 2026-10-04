import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .config import get_settings
from .core.netinfo import server_url_for_clients
from .database import Base, SessionLocal, engine
from .routers import auth, public, student
from .services.auth import ensure_default_admin
from .services.seed import seed_schools
from .services.settings import seed_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)

logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("exam.server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger("exam.main")

    from .database import Base, engine
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        ensure_default_admin(db)
        seed_schools(db)
        seed_settings(db)
    finally:
        db.close()

    settings = get_settings()
    url = server_url_for_clients(settings.server_port)

    logger.info("=== Конфигурация сервера ===")
    logger.info("secret_key: %s...%s", settings.secret_key[:8], settings.secret_key[-4:])
    logger.info("database_url: %s", settings.database_url)
    logger.info("================================")
    logger.info("Сервер экзамена запущен")
    logger.info("Адрес для клиентов:   %s", url)
    logger.info("Swagger-документация: %s/docs", url)
    logger.info("================================")

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Сервер экзаменационной системы",
        version="0.2.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(student.router)

    @app.get("/api/health", tags=["service"])
    def health():
        return {"status": "ok"}

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Ошибка базы данных: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка базы данных"},
        )

    return app


app = create_app()