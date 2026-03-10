from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.campaign_state import CampaignState

PHASE_REGISTRY: dict[str, dict[str, str]] = {
    "HUB": {
        "label": "拠点",
        "summary": "休息、買い物、装備変更、次の準備を行う。",
    },
    "INTERACTION": {
        "label": "交流",
        "summary": "仲間やNPCと話し、信頼や印象を変える。",
    },
    "INVESTIGATION": {
        "label": "調査",
        "summary": "聞き込みや現地確認で手がかりを集める。",
    },
    "EXPEDITION": {
        "label": "危険地帯",
        "summary": "ダンジョンや危険地帯に踏み込み、消耗と判断を重ねる。",
    },
    "BATTLE": {
        "label": "戦闘",
        "summary": "個別戦闘で戦術と指揮を試される。",
    },
    "WAR": {
        "label": "戦局",
        "summary": "大規模戦や前線の支援先を選ぶ。",
    },
    "WORLD": {
        "label": "世界・継承",
        "summary": "世界動向、年表、周回や継承を確認する。",
    },
}

TIME_SLOTS = ["MORNING", "DAY", "EVENING", "NIGHT"]


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


def normalize_phase_key(phase_key: str) -> str:
    normalized = str(phase_key or "").upper().strip()
    if normalized not in PHASE_REGISTRY:
        raise ValueError(f"unsupported campaign phase: {phase_key}")
    return normalized


def get_phase_metadata(phase_key: str) -> dict[str, str]:
    return PHASE_REGISTRY[normalize_phase_key(phase_key)].copy()


def list_available_phase_options() -> list[dict[str, str]]:
    return [
        {
            "phase_key": phase_key,
            "label": metadata["label"],
            "summary": metadata["summary"],
        }
        for phase_key, metadata in PHASE_REGISTRY.items()
    ]


def get_or_create_campaign_state(db: Session, world_id: int) -> CampaignState:
    state = db.query(CampaignState).filter(CampaignState.world_id == world_id).first()
    if state:
        return state

    state = CampaignState(
        world_id=world_id,
        current_phase="HUB",
        day_no=1,
        time_slot="MORNING",
        narrative_state_json=_dump_json_dict(
            {
                "tone": "calm",
                "weight": "normal",
                "recent_event": "arrival",
            }
        ),
        phase_context_json=_dump_json_dict({}),
    )
    db.add(state)
    db.flush()
    return state


def read_narrative_state(state: CampaignState) -> dict[str, Any]:
    return _safe_load_json_dict(state.narrative_state_json)


def write_narrative_state(state: CampaignState, data: dict[str, Any]) -> None:
    state.narrative_state_json = _dump_json_dict(data)


def read_phase_context(state: CampaignState) -> dict[str, Any]:
    return _safe_load_json_dict(state.phase_context_json)


def write_phase_context(state: CampaignState, data: dict[str, Any]) -> None:
    state.phase_context_json = _dump_json_dict(data)


def advance_time_slot(state: CampaignState) -> None:
    current = str(state.time_slot or "MORNING").upper().strip()
    if current not in TIME_SLOTS:
        state.time_slot = "MORNING"
        return

    index = TIME_SLOTS.index(current)
    if index == len(TIME_SLOTS) - 1:
        state.day_no += 1
        state.time_slot = TIME_SLOTS[0]
        return

    state.time_slot = TIME_SLOTS[index + 1]


def transition_campaign_phase(
    db: Session,
    *,
    world_id: int,
    target_phase: str,
) -> tuple[CampaignState, str]:
    state = get_or_create_campaign_state(db, world_id)
    previous_phase = state.current_phase
    normalized_target = normalize_phase_key(target_phase)
    if normalized_target != previous_phase:
        state.current_phase = normalized_target
        advance_time_slot(state)

    narrative_state = read_narrative_state(state)
    narrative_state["recent_event"] = f"phase:{normalized_target.lower()}"

    if normalized_target == "HUB":
        narrative_state["tone"] = "calm"
        narrative_state["weight"] = "normal"
    elif normalized_target in {"INTERACTION", "INVESTIGATION"}:
        narrative_state["tone"] = "uneasy"
        narrative_state["weight"] = "normal"
    elif normalized_target == "EXPEDITION":
        narrative_state["tone"] = "tense"
        narrative_state["weight"] = "major"
    elif normalized_target == "BATTLE":
        narrative_state["tone"] = "desperate"
        narrative_state["weight"] = "major"
    elif normalized_target == "WAR":
        narrative_state["tone"] = "desperate"
        narrative_state["weight"] = "climax"
    else:
        narrative_state["tone"] = "mournful"
        narrative_state["weight"] = "major"

    write_narrative_state(state, narrative_state)
    db.add(state)
    db.flush()
    return state, previous_phase
