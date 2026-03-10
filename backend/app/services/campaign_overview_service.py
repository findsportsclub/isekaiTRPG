from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.quest import Quest
from app.models.world import World
from app.services.campaign_phase_service import (
    get_or_create_campaign_state,
    list_available_phase_options,
    read_phase_context,
)
from app.services.expedition_service import get_expedition_context, is_expedition_location
from app.services.faction_service import list_faction_incident_hints
from app.services.war_service import get_war_state_snapshot
from app.services.world_progress_service import get_or_create_world_state

PHASE_ROUTE_MAP = {
    "HUB": "/api/hub/worlds/{world_id}",
    "INTERACTION": "/api/interaction/worlds/{world_id}",
    "INVESTIGATION": "/api/investigation/worlds/{world_id}",
    "EXPEDITION": "/api/expedition/worlds/{world_id}",
    "BATTLE": "/api/battles",
    "WAR": "/api/war/worlds/{world_id}",
    "WORLD": "/api/continuity/worlds/{world_id}",
}


def build_phase_context_hints(db: Session, *, world: World) -> list[str]:
    world_state = get_or_create_world_state(db, world.world_id)
    campaign_state = get_or_create_campaign_state(db, world.world_id)
    context = read_phase_context(campaign_state)
    hints = [
        f"main_event:{world_state.main_event_title}",
        f"quest_progress:{world_state.quest_progress}",
        f"location:{world.current_location}",
        f"security:{world_state.security_score}",
    ]

    expedition_context = context.get("expedition", {})
    if isinstance(expedition_context, dict) and expedition_context:
        hints.append(
            "expedition:"
            f"stage={int(expedition_context.get('progress_stage', 0) or 0)},"
            f"danger={str(expedition_context.get('danger_level', 'low'))}"
        )

    war_context = context.get("war", {})
    if isinstance(war_context, dict) and war_context:
        hints.append(
            "war:"
            f"pressure={int(war_context.get('war_pressure', 0) or 0)},"
            f"morale={int(war_context.get('allied_morale', 0) or 0)}"
        )

    hints.extend(list_faction_incident_hints(db, world=world, limit=2))

    return hints


def _build_phase_hint(
    db: Session,
    *,
    world: World,
    phase_key: str,
    main_quest: Quest | None,
) -> str:
    if phase_key == "HUB":
        return f"{world.current_location}で準備や休息ができる。"
    if phase_key == "INTERACTION":
        return "主要NPCとの会話で信頼や印象を動かせる。"
    if phase_key == "INVESTIGATION":
        return "手がかりを探り、主線の進行を少しずつ押し進める。"
    if phase_key == "EXPEDITION":
        context = get_expedition_context(db, world_id=world.world_id)
        return (
            f"危険地帯の進行度 {int(context['progress_stage'])}、"
            f"危険度 {str(context['danger_level'])}。"
        )
    if phase_key == "BATTLE":
        return "戦闘開始後に個別解決へ進む。"
    if phase_key == "WAR":
        snapshot = get_war_state_snapshot(db, world_id=world.world_id)
        return (
            f"戦局圧 {int(snapshot['war_pressure'])}、"
            f"味方士気 {int(snapshot['allied_morale'])}。"
        )
    progress = int(main_quest.progress if main_quest else 0)
    return f"主線進行 {progress}。継承候補や記録を確認できる。"


def build_campaign_phase_options(db: Session, *, world: World) -> list[dict[str, str | bool]]:
    world_state = get_or_create_world_state(db, world.world_id)
    main_quest = (
        db.query(Quest)
        .filter(Quest.world_id == world.world_id, Quest.category == "main")
        .first()
    )

    recommended_phase = "INTERACTION"
    if world.current_location == "北坑道前":
        recommended_phase = "EXPEDITION"
    elif world_state.quest_progress >= 3:
        recommended_phase = "WORLD"
    elif world_state.dungeon_score >= 52:
        recommended_phase = "INVESTIGATION"

    options: list[dict[str, str | bool]] = []
    for item in list_available_phase_options():
        phase_key = str(item["phase_key"])
        enabled = True
        if phase_key == "EXPEDITION" and not is_expedition_location(world):
            enabled = False

        options.append(
            {
                "phase_key": phase_key,
                "label": str(item["label"]),
                "summary": str(item["summary"]),
                "route_path": PHASE_ROUTE_MAP[phase_key].format(world_id=world.world_id),
                "enabled": enabled,
                "recommended": phase_key == recommended_phase and enabled,
                "state_hint": _build_phase_hint(
                    db,
                    world=world,
                    phase_key=phase_key,
                    main_quest=main_quest,
                ),
            }
        )
    return options
