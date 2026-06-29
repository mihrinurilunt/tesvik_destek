from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.schemas import HealthResponse, MatchRequest
from shared.exceptions import AppException, MatchingException
from shared.logger import get_logger
from shared.models import MatchResult
from shared.response_utils import error_message
from matcher import Matcher

logger = get_logger(__name__)

app = FastAPI(title="Matching Service", version="1.0.0")

matcher = Matcher()


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(
        "AppException raised",
        extra={"error_code": exc.error_code, "err_message": exc.message, "details": exc.details},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_message(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception in matching_service")
    return JSONResponse(
        status_code=500,
        content=error_message(
            code="INTERNAL_ERROR",
            message="Beklenmeyen bir hata oluştu.",
            details={"error": str(exc)},
        ),
    )


@app.post("/match", response_model=list[MatchResult])
async def match(request: MatchRequest) -> list[MatchResult]:
    """
    Kullanıcı profiline göre uygun teşvik/destek programlarını skorlar.
    Doğrudan MatchResult listesi döner.
    """
    logger.info(
        "Match request received",
        extra={
            "sector": request.user_profile.sector,
            "employee_count": request.user_profile.employee_count,
            "top_k": request.top_k,
        },
    )

    try:
        matches = await matcher.find_matches(
            user_profile=request.user_profile,
            top_k=request.top_k,
        )
    except MatchingException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error during matching")
        raise MatchingException(
            message="Matching işlemi sırasında beklenmeyen bir hata oluştu.",
            details={"service": "matching_service", "error": str(exc)},
        ) from exc

    logger.info("Matching completed", extra={"match_count": len(matches)})

    return matches


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="matching_service", status="ok")