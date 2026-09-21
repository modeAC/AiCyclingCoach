from __future__ import annotations

import os
from datetime import date
from typing import Any
from urllib.parse import quote

import httpx


class IntervalsError(RuntimeError):
    """A safe, user-facing Intervals.icu API error."""


class IntervalsClient:
    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        if not api_key.strip():
            raise ValueError("INTERVALS_API_KEY is required")
        self._http = httpx.Client(
            base_url="https://intervals.icu/api/v1",
            auth=("API_KEY", api_key),
            timeout=timeout,
            transport=transport,
        )

    @classmethod
    def from_env(cls) -> IntervalsClient:
        return cls(os.environ.get("INTERVALS_API_KEY", ""))

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise IntervalsError("Intervals.icu request timed out") from exc
        except httpx.RequestError as exc:
            raise IntervalsError("Could not reach Intervals.icu") from exc

        if response.status_code == 401:
            raise IntervalsError("Intervals.icu authentication failed")
        if response.status_code == 403:
            raise IntervalsError("Intervals.icu denied this operation")
        if response.status_code == 429:
            raise IntervalsError("Intervals.icu rate limit exceeded; retry later")
        if response.is_error:
            raise IntervalsError(f"Intervals.icu returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise IntervalsError("Intervals.icu returned malformed JSON") from exc

    def get_athlete(self) -> dict[str, Any]:
        return self._request("GET", "/athlete/0")

    def list_activities(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/athlete/0/activities",
            params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        )

    def get_activity(self, activity_id: str) -> dict[str, Any]:
        activity = quote(activity_id, safe="")
        return self._request("GET", f"/activity/{activity}", params={"intervals": "true"})

    def list_wellness(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/athlete/0/wellness",
            params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        )

    def list_events(self, oldest: date, newest: date) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            "/athlete/0/events",
            params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
        )

    def upsert_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._request(
            "POST",
            "/athlete/0/events/bulk",
            params={"upsert": "true"},
            json=events,
        )

    def delete_events(self, event_refs: list[dict[str, Any]]) -> int:
        return self._request(
            "PUT", "/athlete/0/events/bulk-delete", json=event_refs
        )
