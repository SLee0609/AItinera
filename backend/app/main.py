import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .errors import ItineraryError, UpstreamError
from .pipeline import generate_itinerary
from .schemas import MAX_CITY_LENGTH, MAX_DAYS, MIN_DAYS, Itinerary, ItineraryRequest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aitinera")

app = FastAPI(title="AItinera API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = {str(part) for err in exc.errors() for part in err.get("loc", ())}
    if "days" in fields:
        message = f"Trip length must be between {MIN_DAYS} and {MAX_DAYS} days."
    elif "city" in fields:
        message = f"Enter a city name of up to {MAX_CITY_LENGTH} characters."
    else:
        message = "Send a JSON body with a city and a number of days."
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(ItineraryError)
async def itinerary_error(_: Request, exc: ItineraryError) -> JSONResponse:
    if isinstance(exc, UpstreamError):
        log.error("Upstream failure: %s", exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    log.exception("Unexpected error", exc_info=exc)
    return JSONResponse(
        status_code=500, content={"detail": "Something went wrong while planning your trip. Try again."}
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/itinerary", response_model=Itinerary, response_model_exclude_none=True)
async def create_itinerary(
    request: ItineraryRequest, settings: Annotated[Settings, Depends(get_settings)]
) -> Itinerary:
    return await generate_itinerary(request.city, request.days, settings)
