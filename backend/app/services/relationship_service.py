from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.world_relationship_state import WorldRelationshipState

NPC_DISPLAY_NAME_MAP = {
    "npc_001": "村長",
    "npc_002": "宿屋の主人",
    "npc_003": "見張りの青年",
    "npc_004": "鉱夫の老人",
    "npc_005": "旅人",
}


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _derive_reaction_label(trust_score: float, affinity_score: float) -> tuple[str, str]:
    if trust_score >= 0.75:
        return "trusted", "かなり打ち解けており、言葉を前向きに受け取りやすい。"
    if trust_score >= 0.45:
        return "warm", "警戒は薄れ、協力的な空気が見え始めている。"
    if trust_score <= -0.35 or affinity_score <= -0.35:
        return "guarded", "相手はまだ距離を取り、言葉の裏を測ろうとしている。"
    return "neutral", "表向きは落ち着いているが、関係はまだ固まりきっていない。"


def get_or_create_relationship_state(
    db: Session,
    *,
    world_id: int,
    target_key: str,
    display_name: str | None = None,
) -> WorldRelationshipState:
    state = (
        db.query(WorldRelationshipState)
        .filter(
            WorldRelationshipState.world_id == world_id,
            WorldRelationshipState.target_key == target_key,
        )
        .first()
    )
    if state:
        return state

    resolved_name = display_name or NPC_DISPLAY_NAME_MAP.get(target_key, target_key)
    label, summary = _derive_reaction_label(0.0, 0.0)
    state = WorldRelationshipState(
        world_id=world_id,
        target_key=target_key,
        display_name=resolved_name,
        trust_score=0.0,
        affinity_score=0.0,
        reaction_label=label,
        reaction_summary=summary,
        interaction_count=0,
        last_interaction_type="none",
    )
    db.add(state)
    db.flush()
    return state


def apply_relationship_delta(
    db: Session,
    *,
    world_id: int,
    target_key: str,
    interaction_type: str,
    trust_delta: float = 0.0,
    affinity_delta: float = 0.0,
    display_name: str | None = None,
) -> WorldRelationshipState:
    state = get_or_create_relationship_state(
        db,
        world_id=world_id,
        target_key=target_key,
        display_name=display_name,
    )
    state.trust_score = round(_clamp(state.trust_score + trust_delta, -1.0, 1.0), 3)
    state.affinity_score = round(_clamp(state.affinity_score + affinity_delta, -1.0, 1.0), 3)
    state.interaction_count += 1
    state.last_interaction_type = interaction_type
    label, summary = _derive_reaction_label(state.trust_score, state.affinity_score)
    state.reaction_label = label
    state.reaction_summary = summary
    db.add(state)
    db.flush()
    return state


def get_relationship_snapshot(
    db: Session,
    *,
    world_id: int,
    target_key: str,
) -> dict[str, str | float | int]:
    state = get_or_create_relationship_state(
        db,
        world_id=world_id,
        target_key=target_key,
    )
    return {
        "target_key": state.target_key,
        "display_name": state.display_name,
        "trust_score": state.trust_score,
        "affinity_score": state.affinity_score,
        "reaction_label": state.reaction_label,
        "reaction_summary": state.reaction_summary,
        "interaction_count": state.interaction_count,
    }


def list_relationship_hints(db: Session, *, world_id: int, limit: int = 5) -> list[dict[str, str | float | int]]:
    states = (
        db.query(WorldRelationshipState)
        .filter(WorldRelationshipState.world_id == world_id)
        .order_by(
            WorldRelationshipState.interaction_count.desc(),
            WorldRelationshipState.relationship_state_id.asc(),
        )
        .limit(limit)
        .all()
    )
    return [
        {
            "target_key": state.target_key,
            "display_name": state.display_name,
            "trust_score": state.trust_score,
            "affinity_score": state.affinity_score,
            "reaction_label": state.reaction_label,
            "reaction_summary": state.reaction_summary,
        }
        for state in states
    ]
