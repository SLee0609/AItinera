"""Step 1: ask Gemini for candidate attractions."""

import logging
from collections.abc import Iterable

from google import genai
from google.genai import types
from pydantic import BaseModel, TypeAdapter, ValidationError

from ..errors import UpstreamError

log = logging.getLogger(__name__)

MIN_VISIT_MINUTES = 15
MAX_VISIT_MINUTES = 360
MAX_DESCRIPTION_CHARS = 200


class Candidate(BaseModel):
    name: str
    description: str
    visit_minutes: int
    neighborhood: str


PROMPT = """You are planning a {days}-day sightseeing trip to {city}.

List exactly {count} distinct tourist attractions in or near {city} that a first-time visitor would \
want to see, ordered from most to least essential.

Rules:
- Each item is one physical place that can be found on Google Maps: a landmark, museum, park, \
market, viewpoint, historic site, or distinctive neighborhood.
- No tours, restaurants, hotels, shops, events, or the city itself.
- Prefer places in the city. Include a place outside it only if it's a classic trip from {city}.
- name: the place's common English name, as it appears on maps.
- description: one sentence of at most 25 words on why it's worth visiting.
- visit_minutes: the typical time a visitor spends there, from {min_visit} to {max_visit}.
- neighborhood: the district or area it's in, as locals name it.
"""

_candidates = TypeAdapter(list[Candidate])


def clean_candidates(items: Iterable[Candidate]) -> list[Candidate]:
    """Trim text, clamp visit times and drop empty or duplicate names, keeping the LLM's order."""
    seen: set[str] = set()
    cleaned: list[Candidate] = []
    for item in items:
        name = " ".join(item.name.split())
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        description = " ".join(item.description.split())
        if len(description) > MAX_DESCRIPTION_CHARS:
            description = description[: MAX_DESCRIPTION_CHARS - 1].rstrip() + "…"
        cleaned.append(
            Candidate(
                name=name,
                description=description,
                visit_minutes=min(MAX_VISIT_MINUTES, max(MIN_VISIT_MINUTES, item.visit_minutes)),
                neighborhood=" ".join(item.neighborhood.split()),
            )
        )
    return cleaned


def _parse(response: types.GenerateContentResponse) -> list[Candidate]:
    if isinstance(response.parsed, list):
        return [c if isinstance(c, Candidate) else Candidate.model_validate(c) for c in response.parsed]
    return _candidates.validate_json(response.text or "")


async def suggest_attractions(
    *,
    api_key: str,
    model: str,
    thinking_level: str,
    city: str,
    days: int,
    count: int,
    attempts: int = 2,
) -> list[Candidate]:
    prompt = PROMPT.format(
        city=city, days=days, count=count, min_visit=MIN_VISIT_MINUTES, max_visit=MAX_VISIT_MINUTES
    )
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[Candidate],
        temperature=0.4,
        thinking_config=types.ThinkingConfig(thinking_level=thinking_level.upper()) if thinking_level else None,
    )
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))
    last_error: Exception | None = None
    try:
        for attempt in range(1, attempts + 1):
            try:
                response = await client.aio.models.generate_content(model=model, contents=prompt, config=config)
                candidates = clean_candidates(_parse(response))
                if candidates:
                    return candidates[:count]
                last_error = ValueError("empty candidate list")
            except (ValidationError, ValueError) as err:
                last_error = err
            except Exception as err:  # SDK and network errors
                last_error = err
            log.warning("Gemini attempt %d/%d failed: %r", attempt, attempts, last_error)
    finally:
        await client.aio.aclose()
    raise UpstreamError(f"Gemini: {last_error!r}")
