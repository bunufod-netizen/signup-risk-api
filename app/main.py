import asyncio
import hmac
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import BulkCheckRequest, CheckRequest, CheckResponse
from app.services.email_checker import check_email

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Signup risk API started")
    yield


app = FastAPI(title="Signup Risk API", version="1.0.0", description="Non-intrusive signup email risk signals.", lifespan=lifespan)
if settings.cors_origin_list:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=False)


@app.middleware("http")
async def production_guard(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})
            if declared_size > settings.max_request_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
        if not content_length:
            body = await request.body()
            if len(body) > settings.max_request_body_bytes:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})

    if request.url.path in {"/check", "/bulk-check"} and settings.rapidapi_proxy_secret:
        supplied_secret = request.headers.get("X-RapidAPI-Proxy-Secret", "")
        if not hmac.compare_digest(supplied_secret, settings.rapidapi_proxy_secret):
            return JSONResponse(status_code=401, content={"detail": "Gateway authentication required"})
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "Signup Risk API", "version": app.version, "status": "online", "docs": "/docs"}


@app.post("/check", response_model=CheckResponse)
async def check(payload: CheckRequest) -> CheckResponse:
    return await check_email(payload.email)


@app.post("/bulk-check", response_model=list[CheckResponse])
async def bulk_check(payload: BulkCheckRequest) -> list[CheckResponse]:
    if len(payload.emails) > settings.max_bulk_emails:
        raise HTTPException(status_code=422, detail=f"A bulk request may contain at most {settings.max_bulk_emails} emails")
    results = await asyncio.gather(*(check_email(email) for email in payload.emails), return_exceptions=True)
    response: list[CheckResponse] = []
    for email, result in zip(payload.emails, results):
        if isinstance(result, Exception):
            logger.warning("Failed to check an email in bulk request", exc_info=result)
            response.append(CheckResponse(email=email.strip(), valid_format=False, domain=None, domain_exists=None, mx_exists=None, disposable=False, role_account=False, free_provider=False, typo_suggestion=None, risk="high", risk_score=100, reasons=["Unable to complete email check"]))
        else:
            response.append(result)
    return response
