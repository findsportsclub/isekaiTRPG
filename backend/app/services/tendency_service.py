from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.world_tendency_state import WorldTendencyState

DEFAULT_TENDENCY_SCORES: dict[str, int] = {
    "honest": 0,
    "cautious": 0,
    "curious": 0,
    "protective": 0,
    "bold": 0,
    "pragmatic": 0,
}


def _safe_load_json_dict(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _dump_json_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def get_or_create_tendency_state(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
) -> WorldTendencyState:
    state = (
        db.query(WorldTendencyState)
        .filter(
            WorldTendencyState.world_id == world_id,
            WorldTendencyState.actor_key == actor_key,
        )
        .first()
    )
    if state:
        return state

    state = WorldTendencyState(
        world_id=world_id,
        actor_key=actor_key,
        tendency_scores_json=_dump_json_dict(DEFAULT_TENDENCY_SCORES),
        last_updated_reason="init",
        update_count=0,
    )
    db.add(state)
    db.flush()
    return state


def read_tendency_scores(state: WorldTendencyState) -> dict[str, int]:
    scores = DEFAULT_TENDENCY_SCORES.copy()
    raw = _safe_load_json_dict(state.tendency_scores_json)
    for key, value in raw.items():
        try:
            scores[key] = int(value)
        except Exception:
            continue
    return scores


def apply_tendency_delta(
    db: Session,
    *,
    world_id: int,
    reason: str,
    deltas: dict[str, int],
    actor_key: str = "hero",
) -> WorldTendencyState:
    state = get_or_create_tendency_state(db, world_id=world_id, actor_key=actor_key)
    scores = read_tendency_scores(state)
    for key, delta in deltas.items():
        scores[key] = int(scores.get(key, 0) or 0) + int(delta or 0)

    state.tendency_scores_json = _dump_json_dict(scores)
    state.last_updated_reason = reason
    state.update_count += 1
    db.add(state)
    db.flush()
    return state


def build_tendency_hint_list(scores: dict[str, int]) -> list[str]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    hints: list[str] = []
    for key, value in ordered[:3]:
        if value <= 0:
            continue
        hints.append(f"{key}:{value}")
    return hints


def get_primary_tendency(scores: dict[str, int]) -> str:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered:
        return "honest"
    key, value = ordered[0]
    if value <= 0:
        return "honest"
    return str(key)
