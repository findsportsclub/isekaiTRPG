from __future__ import annotations

import json
from sqlalchemy.orm import Session

from app.services.battle_registry import get_equipment
from app.models.log import Log
from app.models.quest import Quest
from app.models.world import World
from app.models.world_state import WorldState
from app.services.campaign_phase_service import (
    get_or_create_campaign_state,
    read_phase_context,
    write_phase_context,
)
from app.services.tendency_service import (
    apply_tendency_delta,
    get_or_create_tendency_state,
    get_primary_tendency,
    read_tendency_scores,
)
from app.services.world_progress_service import get_security_band, get_or_create_world_state

EXPEDITION_ENABLED_LOCATIONS = {"北坑道前"}


def is_expedition_location(world: World) -> bool:
    return world.current_location in EXPEDITION_ENABLED_LOCATIONS


def get_expedition_context(db: Session, *, world_id: int) -> dict[str, int | str]:
    campaign_state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(campaign_state)
    expedition = context.get("expedition", {})
    if not isinstance(expedition, dict):
        expedition = {}

    progress_stage = int(expedition.get("progress_stage", 0) or 0)
    supply_pressure = int(expedition.get("supply_pressure", 0) or 0)
    danger_level = str(expedition.get("danger_level", "low") or "low")
    gathered_materials = expedition.get("gathered_materials", {})
    if not isinstance(gathered_materials, dict):
        gathered_materials = {}
    return {
        "progress_stage": progress_stage,
        "supply_pressure": supply_pressure,
        "danger_level": danger_level,
        "gathered_materials": gathered_materials,
    }


def set_expedition_context(
    db: Session,
    *,
    world_id: int,
    progress_stage: int,
    supply_pressure: int,
    danger_level: str,
    gathered_materials: dict[str, int] | None = None,
) -> dict[str, int | str]:
    campaign_state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(campaign_state)
    context["expedition"] = {
        "progress_stage": max(0, progress_stage),
        "supply_pressure": max(0, supply_pressure),
        "danger_level": danger_level,
        "gathered_materials": dict(gathered_materials or {}),
    }
    write_phase_context(campaign_state, context)
    db.add(campaign_state)
    db.flush()
    return {
        "progress_stage": max(0, progress_stage),
        "supply_pressure": max(0, supply_pressure),
        "danger_level": danger_level,
        "gathered_materials": dict(gathered_materials or {}),
    }


def list_expedition_options(world: World) -> list[dict[str, str]]:
    if not is_expedition_location(world):
        return []
    return [
        {"option_key": "advance", "label": "奥へ進む", "summary": "危険を承知で手がかりの核心へ近づく。"},
        {"option_key": "gather", "label": "鉱石と素材を集める", "summary": "足元や壁面を探り、鉱石や魔石の欠片を確保する。"},
        {"option_key": "camp", "label": "一度立て直す", "summary": "足を止め、警戒を維持しつつ態勢を整える。"},
        {"option_key": "withdraw", "label": "引き返す", "summary": "消耗が深まる前に村側へ戻る。"},
    ]


def build_expedition_option_suggestions(
    db: Session,
    *,
    world: World,
) -> dict[str, object]:
    context = get_expedition_context(db, world_id=world.world_id)
    tendency_state = get_or_create_tendency_state(db, world_id=world.world_id)
    primary = get_primary_tendency(read_tendency_scores(tendency_state))

    progress_stage = int(context["progress_stage"])
    supply_pressure = int(context["supply_pressure"])
    danger_level = str(context["danger_level"])

    if danger_level == "high" or supply_pressure >= 3:
        recommended_option_key = "withdraw"
        recommended_reason = "危険と消耗が高く、ここで深追いすると退路を失いやすい。"
    elif progress_stage >= 1 and primary in {"curious", "pragmatic"} and supply_pressure <= 1:
        recommended_option_key = "gather"
        recommended_reason = "足場と空気に少し余裕がある今なら、鉱石や魔石の回収で追加の利益を狙える。"
    elif supply_pressure >= 1 and primary in {"cautious", "protective"}:
        recommended_option_key = "camp"
        recommended_reason = "慎重寄りの現状では、一度立て直してから進む方が安定する。"
    elif progress_stage < 2:
        recommended_option_key = "advance"
        recommended_reason = "まだ進行が浅く、もう一歩踏み込むことで手がかりと成果が増えやすい。"
    else:
        recommended_option_key = "camp"
        recommended_reason = "成果は十分に近いので、ここで消耗を整える方が崩れにくい。"

    options = []
    for item in list_expedition_options(world):
        fallback_reason = "危険地帯で取れる基本行動の一つ。"
        options.append(
            {
                **item,
                "recommended": item["option_key"] == recommended_option_key,
                "reason": recommended_reason if item["option_key"] == recommended_option_key else fallback_reason,
            }
        )

    return {
        "recommended_option_key": recommended_option_key,
        "options": options,
    }


def build_expedition_encounter_hint(
    db: Session,
    *,
    world: World,
) -> str:
    state = get_or_create_world_state(db, world.world_id)
    context = get_expedition_context(db, world_id=world.world_id)
    security_band = get_security_band(state.security_score)
    danger_level = str(context["danger_level"])

    if security_band in {"unstable", "lawless"} and danger_level in {"medium", "high"}:
        return "坑道前の往来も荒れており、魔物だけでなく物資狙いの盗賊に遭遇する危険が高い。"
    if security_band in {"unstable", "lawless"}:
        return "周辺治安の悪化で、坑道へ向かう道にも追い剥ぎや盗賊斥候の気配が増えている。"
    if danger_level in {"medium", "high"}:
        return "坑道の深部へ近づくほど、不意の戦闘や崩落に巻き込まれる危険が増す。"
    return "今のところ目立つ待ち伏せの気配は薄いが、油断できるほど安全ではない。"


def build_expedition_equipment_support_summary(db: Session, *, world_id: int) -> tuple[str, str]:
    campaign_state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(campaign_state)
    hub = context.get("hub", {})
    if not isinstance(hub, dict):
        hub = {}
    purchased = list(hub.get("purchased_equipment", []) or [])
    if not purchased:
        return "[]", "探索を後押しする購入装備はまだ拠点にない。"
    names: list[str] = []
    for equipment_key in purchased:
        equipment = get_equipment(str(equipment_key))
        if equipment:
            names.append(equipment.name)
    if not names:
        return json.dumps(purchased, ensure_ascii=False), "生成装備はあるが、詳細補正はまだ探索へ接続されていない。"
    return json.dumps(purchased, ensure_ascii=False), " / ".join(names[:3]) + " が探索の備えとして保管されている。"


def _derive_danger_level(progress_stage: int, supply_pressure: int) -> str:
    pressure = progress_stage + supply_pressure
    if pressure >= 5:
        return "high"
    if pressure >= 3:
        return "medium"
    return "low"


def execute_expedition_action(
    db: Session,
    *,
    world: World,
    state: WorldState,
    main_quest: Quest | None,
    option_key: str,
) -> tuple[str, str, dict[str, int | str]]:
    if not is_expedition_location(world):
        raise ValueError("current location does not support expedition")

    context = get_expedition_context(db, world_id=world.world_id)
    progress_stage = int(context["progress_stage"])
    supply_pressure = int(context["supply_pressure"])
    gathered_materials = dict(context.get("gathered_materials", {}) or {})

    if option_key == "advance":
        progress_stage += 1
        supply_pressure += 1
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="expedition:advance",
            deltas={"bold": 1, "curious": 1},
        )
        if progress_stage >= 2:
            state.dungeon_score += 1
            if main_quest and main_quest.status != "CLEARED":
                main_quest.progress += 1
                state.quest_progress += 1
        summary = "慎重に足場を確かめながら坑道の奥へ進み、空気の異様さがさらに濃くなるのを感じた。"
        result_type = "progress"
    elif option_key == "gather":
        ore_amount = 1 + (1 if progress_stage >= 1 else 0)
        shard_amount = 1 if progress_stage >= 2 else 0
        gathered_materials["iron_ore"] = int(gathered_materials.get("iron_ore", 0) or 0) + ore_amount
        if shard_amount > 0:
            gathered_materials["mana_shard"] = int(gathered_materials.get("mana_shard", 0) or 0) + shard_amount
        supply_pressure += 1
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="expedition:gather",
            deltas={"curious": 1, "pragmatic": 1},
        )
        summary = (
            f"壁面の脈を探って鉱石を切り出し、"
            f"{ore_amount}個の鉄鉱石"
            + (f"と {shard_amount}個の魔石片" if shard_amount > 0 else "")
            + "を確保した。"
        )
        result_type = "gather"
    elif option_key == "camp":
        supply_pressure = max(0, supply_pressure - 1)
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="expedition:camp",
            deltas={"cautious": 1, "protective": 1},
        )
        summary = "いったん足を止め、灯りと退路を確かめながら呼吸を整えた。"
        result_type = "recovery"
    elif option_key == "withdraw":
        world.current_location = "村の入口"
        progress_stage = 0
        supply_pressure = 0
        apply_tendency_delta(
            db,
            world_id=world.world_id,
            reason="expedition:withdraw",
            deltas={"cautious": 1},
        )
        summary = "無理を避け、坑道前から一度退いて態勢を立て直すことにした。"
        result_type = "withdraw"
    else:
        raise ValueError(f"unsupported expedition option: {option_key}")

    danger_level = _derive_danger_level(progress_stage, supply_pressure)
    expedition_context = set_expedition_context(
        db,
        world_id=world.world_id,
        progress_stage=progress_stage,
        supply_pressure=supply_pressure,
        danger_level=danger_level,
        gathered_materials=gathered_materials,
    )

    db.add(
        Log(
            world_id=world.world_id,
            log_type="expedition",
            title="危険地帯: 進行",
            body=summary,
        )
    )
    db.add(state)
    db.add(world)
    if main_quest:
        db.add(main_quest)
    db.flush()
    return summary, result_type, expedition_context


def serialize_gathered_materials(context: dict[str, int | str | dict[str, int]]) -> str:
    return json.dumps(dict(context.get("gathered_materials", {}) or {}), ensure_ascii=False)
