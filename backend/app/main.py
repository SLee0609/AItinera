import logging
import re
import secrets
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth import current_user, optional_user
from .config import Settings, get_settings
from .errors import ItineraryError, ItineraryNotFound, StorageError, UpstreamError
from .pipeline import generate_itinerary
from .schemas import (
    MAX_CITY_LENGTH,
    MAX_DAYS,
    MIN_DAYS,
    AccountDeletion,
    Itinerary,
    ItineraryRequest,
    SavedItinerarySummary,
    SavedStatus,
)
from .services.supabase import Store

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aitinera")

app = FastAPI(title="AItinera API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Itinerary IDs: secrets.token_urlsafe(9), 12 URL-safe characters (72 random bits).
ITINERARY_ID = re.compile(r"[A-Za-z0-9_-]{12}")
STORAGE_TIMEOUT_S = 5.0


def new_itinerary_id() -> str:
    return secrets.token_urlsafe(9)


async def get_store(settings: Annotated[Settings, Depends(get_settings)]) -> AsyncIterator[Store | None]:
    """A Supabase store for this request, or None when Supabase isn't configured."""
    if not settings.storage_configured:
        yield None
        return
    async with httpx.AsyncClient(timeout=STORAGE_TIMEOUT_S) as client:
        yield Store(client, settings.supabase_base_url, settings.supabase_secret_key)


def require_store(store: Annotated[Store | None, Depends(get_store)]) -> Store:
    if store is None:
        raise StorageError("Supabase isn't configured")
    return store


def check_id(itinerary_id: str) -> str:
    if not ITINERARY_ID.fullmatch(itinerary_id):
        raise ItineraryNotFound()
    return itinerary_id


UserId = Annotated[str, Depends(current_user)]
RequiredStore = Annotated[Store, Depends(require_store)]


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
    if isinstance(exc, UpstreamError | StorageError):
        log.error("%s: %s", type(exc).__name__, exc.detail)
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
    request: ItineraryRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[Store | None, Depends(get_store)],
    user_id: Annotated[str | None, Depends(optional_user)],
) -> Itinerary:
    itinerary = await generate_itinerary(request.city, request.days, settings)
    if store is None:
        return itinerary
    # Stored exactly as served (without the ID), so share links show the same trip.
    data = itinerary.model_dump(mode="json", by_alias=True, exclude_none=True, exclude={"id"})
    itinerary_id = new_itinerary_id()
    try:
        await store.insert_itinerary(itinerary_id, request.city, request.days, data, user_id)
    except ItineraryError as err:
        # The trip still displays; only sharing and saving are unavailable.
        log.error("Couldn't store itinerary: %s", getattr(err, "detail", err))
        return itinerary
    return itinerary.model_copy(update={"id": itinerary_id})


@app.get("/api/itinerary/{itinerary_id}", response_model=Itinerary, response_model_exclude_none=True)
async def get_itinerary(itinerary_id: str, store: RequiredStore) -> Itinerary:
    data = await store.get_itinerary(check_id(itinerary_id))
    if data is None:
        raise ItineraryNotFound()
    return Itinerary.model_validate({**data, "id": itinerary_id})


@app.get("/api/saved", response_model=list[SavedItinerarySummary])
async def list_saved(user_id: UserId, store: RequiredStore) -> list[SavedItinerarySummary]:
    return [SavedItinerarySummary.model_validate(row) for row in await store.list_saved(user_id)]


@app.get("/api/saved/{itinerary_id}", response_model=SavedStatus)
async def saved_status(itinerary_id: str, user_id: UserId, store: RequiredStore) -> SavedStatus:
    return SavedStatus(saved=await store.is_saved(user_id, check_id(itinerary_id)))


@app.put("/api/saved/{itinerary_id}", response_model=SavedStatus)
async def save_itinerary(itinerary_id: str, user_id: UserId, store: RequiredStore) -> SavedStatus:
    await store.save(user_id, check_id(itinerary_id))
    return SavedStatus(saved=True)


@app.delete("/api/saved/{itinerary_id}", response_model=SavedStatus)
async def unsave_itinerary(itinerary_id: str, user_id: UserId, store: RequiredStore) -> SavedStatus:
    await store.unsave(user_id, check_id(itinerary_id))
    return SavedStatus(saved=False)


@app.delete("/api/account", response_model=AccountDeletion)
async def delete_account(user_id: UserId, store: RequiredStore) -> AccountDeletion:
    """Deletes the signed-in user's account. Their access token stays valid until it expires (about an hour),
    so the frontend signs out right after; a later request with it can't recreate any data for the user."""
    await store.delete_user(user_id)
    log.info("Deleted account %s", user_id)
    return AccountDeletion(deleted=True)
