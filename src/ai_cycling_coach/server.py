from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from .intervals import IntervalsClient, IntervalsError

OWNER_PREFIX = "ai-cycling-coach:"


class Workout(BaseModel):
    date: date
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class ReviewNote(BaseModel):
    date: date
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


def _range(oldest: str, newest: str, maximum_days: int) -> tuple[date, date]:
    start = date.fromisoformat(oldest)
    end = date.fromisoformat(newest)
    if start > end:
        raise ValueError("oldest must not be after newest")
    if (end - start).days + 1 > maximum_days:
        raise ValueError(f"date range must be at most {maximum_days} days")
    return start, end


def _tool_range(oldest: str, newest: str, maximum_days: int) -> tuple[date, date]:
    try:
        return _range(oldest, newest, maximum_days)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def _event_payloads(
    start: date,
    end: date,
    workouts: list[Workout],
    review_note: ReviewNote,
) -> list[dict[str, Any]]:
    if not workouts:
        raise ValueError("at least one workout is required")
    positions: defaultdict[date, int] = defaultdict(int)
    events: list[dict[str, Any]] = []
    period = f"{start.isoformat()}:{end.isoformat()}"
    for workout in workouts:
        if not start <= workout.date <= end:
            raise ValueError("every workout date must be inside the plan range")
        if not workout.name.strip() or not workout.description.strip():
            raise ValueError("workout name and description must not be blank")
        positions[workout.date] += 1
        external_id = (
            f"{OWNER_PREFIX}{period}:workout:{workout.date.isoformat()}:"
            f"{positions[workout.date]}"
        )
        events.append(
            {
                "category": "WORKOUT",
                "type": "Ride",
                "start_date_local": f"{workout.date.isoformat()}T00:00:00",
                "name": workout.name,
                "description": workout.description,
                "external_id": external_id,
            }
        )
    if not start <= review_note.date <= end:
        raise ValueError("review note date must be inside the plan range")
    if not review_note.title.strip() or not review_note.description.strip():
        raise ValueError("review note title and description must not be blank")
    events.append(
        {
            "category": "NOTE",
            "start_date_local": f"{review_note.date.isoformat()}T00:00:00",
            "name": review_note.title,
            "description": review_note.description,
            "external_id": f"{OWNER_PREFIX}{period}:review",
        }
    )
    external_ids = [event["external_id"] for event in events]
    if len(external_ids) != len(set(external_ids)):
        raise ValueError("generated event IDs must be unique")
    return events


def build_server(client: IntervalsClient | None = None) -> MCPServer:
    mcp = MCPServer(
        "AI Cycling Coach",
        instructions=(
            "Read Intervals.icu data as needed. Before replace_training_plan, present "
            "the complete plan outline and obtain one explicit user approval. Pass "
            "approved=true only after that approval."
        ),
    )
    api = client

    def get_api() -> IntervalsClient:
        nonlocal api
        if api is None:
            api = IntervalsClient.from_env()
        return api

    @mcp.tool()
    def connection_status() -> dict[str, Any]:
        athlete = get_api().get_athlete()
        return {
            "connected": True,
            "athlete": {key: athlete.get(key) for key in ("id", "name")},
        }

    @mcp.tool()
    def get_athlete_profile() -> dict[str, Any]:
        return {"athlete": get_api().get_athlete()}

    @mcp.tool()
    def list_activities(oldest: str, newest: str) -> dict[str, Any]:
        start, end = _tool_range(oldest, newest, 366)
        return {"activities": get_api().list_activities(start, end)}

    @mcp.tool()
    def get_activity_details(activity_id: str) -> dict[str, Any]:
        return {"activity": get_api().get_activity(activity_id)}

    @mcp.tool()
    def list_wellness(oldest: str, newest: str) -> dict[str, Any]:
        start, end = _tool_range(oldest, newest, 366)
        return {"wellness": get_api().list_wellness(start, end)}

    @mcp.tool()
    def list_calendar(oldest: str, newest: str) -> dict[str, Any]:
        start, end = _tool_range(oldest, newest, 366)
        return {"events": get_api().list_events(start, end)}

    @mcp.tool()
    def replace_training_plan(
        oldest: str,
        newest: str,
        workouts: list[Workout],
        review_note: ReviewNote,
        approved: bool,
    ) -> dict[str, int]:
        """Replace integration-owned events after approval of the complete plan."""
        if not approved:
            raise ToolError("whole-plan approval is required before writing")
        start, end = _tool_range(oldest, newest, 42)
        try:
            new_events = _event_payloads(start, end, workouts, review_note)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        new_ids = {event["external_id"] for event in new_events}
        intervals = get_api()
        try:
            existing = intervals.list_events(start, end)
            stale_ids = sorted(
                event["external_id"]
                for event in existing
                if isinstance(event.get("external_id"), str)
                and event["external_id"].startswith(OWNER_PREFIX)
                and event["external_id"] not in new_ids
            )
            upserted = intervals.upsert_events(new_events)
        except IntervalsError as exc:
            raise ToolError(str(exc)) from exc
        deleted = 0
        if stale_ids:
            try:
                deleted = intervals.delete_events(
                    [{"external_id": external_id} for external_id in stale_ids]
                )
            except IntervalsError as exc:
                raise ToolError(
                    "Plan was written, but stale generated events were not removed: "
                    f"{exc}"
                ) from exc
        return {"upserted": len(upserted), "deleted": deleted}

    return mcp


mcp = build_server()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
