from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.world import World
from app.models.world_state import WorldState
from app.services.campaign_phase_service import (
    get_or_create_campaign_state,
    read_phase_context,
    write_phase_context,
)
from app.services.hub_service import get_hub_resource_snapshot
from app.services.tendency_service import (
    apply_tendency_delta,
    get_or_create_tendency_state,
    get_primary_tendency,
    read_tendency_scores,
)
from app.services.world_progress_service import clamp_security_score, sync_security_side_quest

WAR_FRONT_REGISTRY: dict[str, dict[str, Any]] = {
    "village_defense": {
        "label": "村外縁の防衛線",
        "base_pressure": 3,
        "summary": "民家へ流れ込む脅威を食い止め、避難の時間を稼ぐ。",
        "result_summary": "村外縁の防衛線に戦力を回し、押し寄せる脅威を辛うじて押し返した。",
    },
    "north_road": {
        "label": "北街道の封鎖",
        "base_pressure": 2,
        "summary": "増援や逃走路を押さえ、戦局の主導権を握る。",
        "result_summary": "北街道を抑え、敵の動線と補給を乱す手応えを得た。",
    },
    "supply_guard": {
        "label": "補給線の死守",
        "base_pressure": 1,
        "summary": "前線の息切れを防ぎ、持久戦に耐える土台を守る。",
        "result_summary": "補給線を守り抜き、味方の踏みとどまる力を支えた。",
    },
}


def _get_war_context(db: Session, *, world_id: int) -> dict[str, Any]:
    campaign_state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(campaign_state)
    war = context.get("war", {})
    if not isinstance(war, dict):
        war = {}
    return {
        "war_pressure": int(war.get("war_pressure", 4) or 4),
        "allied_morale": int(war.get("allied_morale", 5) or 5),
        "defended_fronts": list(war.get("defended_fronts", []) or []),
    }


def _set_war_context(
    db: Session,
    *,
    world_id: int,
    war_pressure: int,
    allied_morale: int,
    defended_fronts: list[str],
) -> dict[str, Any]:
    campaign_state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(campaign_state)
    context["war"] = {
        "war_pressure": max(0, war_pressure),
        "allied_morale": max(0, allied_morale),
        "defended_fronts": defended_fronts,
    }
    write_phase_context(campaign_state, context)
    db.add(campaign_state)
    db.flush()
    return {
        "war_pressure": max(0, war_pressure),
        "allied_morale": max(0, allied_morale),
        "defended_fronts": defended_fronts,
    }


def list_war_fronts(db: Session, *, world_id: int) -> list[dict[str, str | int]]:
    context = _get_war_context(db, world_id=world_id)
    defended = set(str(item) for item in context["defended_fronts"])
    pressure_modifier = int(context["war_pressure"])
    items: list[dict[str, str | int]] = []
    for front_key, front in WAR_FRONT_REGISTRY.items():
        pressure = int(front["base_pressure"]) + max(0, pressure_modifier - 3)
        if front_key in defended:
            pressure = max(0, pressure - 1)
        items.append(
            {
                "front_key": front_key,
                "label": str(front["label"]),
                "pressure": pressure,
                "summary": str(front["summary"]),
            }
        )
    return items


def build_war_front_suggestions(
    db: Session,
    *,
    world: World,
) -> dict[str, object]:
    snapshot = get_war_state_snapshot(db, world_id=world.world_id)
    tendency_state = get_or_create_tendency_state(db, world_id=world.world_id)
    primary = get_primary_tendency(read_tendency_scores(tendency_state))

    if int(snapshot["war_pressure"]) >= 5:
        recommended_front_key = "village_defense"
        recommended_reason = "前線圧が高く、まずは被害が直接広がる村外縁を支える必要がある。"
    elif primary in {"cautious", "protective"}:
        recommended_front_key = "supply_guard"
        recommended_reason = "慎重寄りの現在は、補給線を守って戦線崩壊を防ぐ方が安定する。"
    elif primary in {"pragmatic", "bold"}:
        recommended_front_key = "north_road"
        recommended_reason = "主導権を取りやすい傾向なので、街道封鎖で敵の流れを断つ判断と相性がよい。"
    else:
        recommended_front_key = "village_defense"
        recommended_reason = "最も損失が見えやすい前線を優先するのが無難。"

    fronts = []
    for item in list_war_fronts(db, world_id=world.world_id):
        fronts.append(
            {
                **item,
                "recommended": item["front_key"] == recommended_front_key,
                "reason": recommended_reason if item["front_key"] == recommended_front_key else "戦局を動かす候補の一つ。",
            }
        )

    return {
        "recommended_front_key": recommended_front_key,
        "fronts": fronts,
    }


def get_war_state_snapshot(db: Session, *, world_id: int) -> dict[str, Any]:
    context = _get_war_context(db, world_id=world_id)
    return {
        "war_pressure": int(context["war_pressure"]),
        "allied_morale": int(context["allied_morale"]),
        "defended_fronts": list(context["defended_fronts"]),
    }


def execute_war_action(
    db: Session,
    *,
    world: World,
    state: WorldState,
    front_key: str,
) -> tuple[str, str, dict[str, Any]]:
    if front_key not in WAR_FRONT_REGISTRY:
        raise ValueError(f"unsupported war front: {front_key}")

    context = _get_war_context(db, world_id=world.world_id)
    defended_fronts = [str(item) for item in context["defended_fronts"]]
    if front_key not in defended_fronts:
        defended_fronts.append(front_key)

    war_pressure = int(context["war_pressure"])
    allied_morale = int(context["allied_morale"])
    pressure_before = war_pressure
    hub_resources = get_hub_resource_snapshot(db, world_id=world.world_id)
    crafted_supplies = dict(hub_resources.get("crafted_supplies", {}) or {})

    war_pressure = max(0, war_pressure - 1)
    allied_morale = min(10, allied_morale + 1)
    if int(crafted_supplies.get("field_repair_kit", 0) or 0) > 0:
        allied_morale = min(10, allied_morale + 1)
    state.faction_score += 1
    security_delta = -1 if pressure_before >= 4 else 0
    if front_key == "village_defense":
        state.demon_score = max(0, state.demon_score - 1)
        security_delta += 2
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="war:village_defense",
            deltas={"protective": 1, "bold": 1},
        )
    elif front_key == "north_road":
        state.dungeon_score += 1
        security_delta += 1
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="war:north_road",
            deltas={"pragmatic": 1, "bold": 1},
        )
    else:
        security_delta += 1
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="war:supply_guard",
            deltas={"cautious": 1, "protective": 1},
        )
    state.security_score = clamp_security_score(state.security_score + security_delta)
    security_band_changed = security_delta != 0
    security_quest = sync_security_side_quest(db, world_id=world.world_id, state=state)

    snapshot = _set_war_context(
        db,
        world_id=world.world_id,
        war_pressure=war_pressure,
        allied_morale=allied_morale,
        defended_fronts=defended_fronts,
    )
    summary = str(WAR_FRONT_REGISTRY[front_key]["result_summary"])
    if int(crafted_supplies.get("field_repair_kit", 0) or 0) > 0:
        summary += " 野戦修理具が前線の立て直しを助け、味方の士気もわずかに持ち直した。"
    if security_band_changed:
        if security_delta > 0:
            summary += " 村と街道の治安もやや持ち直し、盗賊崩れの動きは少し鈍った。"
        else:
            summary += " ただし戦火の余波で治安はさらに揺らぎ、追い剥ぎの噂が広がっている。"
    if security_quest and security_quest.status == "ACTIVE" and state.security_score <= 45:
        summary += " 盗賊討伐の依頼も増え、別働隊の手当てが必要そうだ。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="war",
            title="戦局: 支援先決定",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "strategic", snapshot
