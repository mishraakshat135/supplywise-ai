import logging
import time

from fastapi import FastAPI, Request

from ..config import settings


def setup_logging() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL.upper(),
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")


def add_request_logging(app: FastAPI) -> None:
    log = logging.getLogger("supplywise.http")

    @app.middleware("http")
    async def _log(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code,
                 (time.perf_counter() - start) * 1000)
        return response
