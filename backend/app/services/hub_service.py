from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.world import World
from app.models.world_combatant_progress import WorldCombatantProgress
from app.models.world_state import WorldState
from app.services.campaign_phase_service import (
    get_or_create_campaign_state,
    read_phase_context,
    write_phase_context,
)
from app.services.expedition_service import get_expedition_context, serialize_gathered_materials
from app.services.faction_service import list_faction_incident_hints
from app.services.generation_content_service import build_market_offers, get_market_offer_by_key, register_market_equipment
from app.services.battle_registry import get_equipment
from app.services.tendency_service import apply_tendency_delta

MOVE_DESTINATION_MAP: dict[str, list[dict[str, str]]] = {
    "はじまりの村": [
        {"location_id": "village_gate", "label": "村の入口", "summary": "街道と北への道を見渡せる。"},
        {"location_id": "inn", "label": "宿屋", "summary": "休息と噂集めに向いている。"},
    ],
    "村の入口": [
        {"location_id": "start_village", "label": "はじまりの村", "summary": "村の中心へ戻る。"},
        {"location_id": "north_mine", "label": "北坑道前", "summary": "異変の発生源に近づく。"},
    ],
    "北坑道前": [
        {"location_id": "village_gate", "label": "村の入口", "summary": "態勢を立て直すため後退する。"},
    ],
    "宿屋": [
        {"location_id": "start_village", "label": "はじまりの村", "summary": "村の広場へ戻る。"},
    ],
}

DESTINATION_LOCATION_MAP: dict[str, str] = {
    "start_village": "はじまりの村",
    "village_gate": "村の入口",
    "north_mine": "北坑道前",
    "inn": "宿屋",
}

CRAFT_RECIPES: dict[str, dict[str, object]] = {
    "field_repair_kit": {
        "label": "野戦修理具",
        "summary": "応急補修や簡易工作に使える道具束。",
        "cost": {"iron_ore": 2},
        "yield": {"field_repair_kit": 1},
    },
    "mana_focus": {
        "label": "魔力焦点具",
        "summary": "魔石片を束ねた簡易触媒。後の魔法支援に繋げやすい。",
        "cost": {"iron_ore": 1, "mana_shard": 1},
        "yield": {"mana_focus": 1},
    },
}

MATERIAL_CREDIT_VALUES = {
    "iron_ore": 4,
    "mana_shard": 7,
}

REST_COST_BY_LOCATION = {
    "宿屋": 8,
    "はじまりの村": 4,
    "村の入口": 3,
    "北坑道前": 2,
}

TRAVEL_COST_BY_DESTINATION = {
    "start_village": 1,
    "village_gate": 1,
    "north_mine": 3,
    "inn": 2,
}

MEAL_COST = 3
GAMBLE_STAKE = 5
TAX_PAYMENT_UNIT = 10
HOUSING_UPGRADE_CHAIN = {
    "lodging": {"next_tier": "room", "cost": 40, "summary": "簡素な寝床から個室へ移り、休息の質と対面の安定感が増す。"},
    "room": {"next_tier": "house", "cost": 120, "summary": "小さな拠点を構え、保管や交渉の面でも余裕が生まれる。"},
}


def _safe_load_json_dict(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def list_hub_move_destinations(world: World) -> list[dict[str, str]]:
    return [item.copy() for item in MOVE_DESTINATION_MAP.get(world.current_location, [])]


def list_recent_rumors(db: Session, *, world_id: int, limit: int = 3) -> list[str]:
    world = db.query(World).filter(World.world_id == world_id).first()
    logs = (
        db.query(Log)
        .filter(Log.world_id == world_id)
        .order_by(Log.log_id.desc())
        .limit(limit)
        .all()
    )
    rumors = [log.body for log in logs if log.body]
    if rumors:
        if world:
            rumors.extend(list_faction_incident_hints(db, world=world, limit=2))
        return rumors[: max(limit, 3)]
    return [
        "北で霧が濃くなっている",
        "坑道で失踪者が出た",
    ]


def list_party_progress_summary(db: Session, *, world_id: int, limit: int = 4) -> list[dict[str, str]]:
    progress_list = (
        db.query(WorldCombatantProgress)
        .filter(WorldCombatantProgress.world_id == world_id)
        .order_by(
            WorldCombatantProgress.updated_from_battle_id.desc(),
            WorldCombatantProgress.progress_id.asc(),
        )
        .limit(limit)
        .all()
    )
    items: list[dict[str, str]] = []
    for progress in progress_list:
        growth = _safe_load_json_dict(progress.growth_stats_json)
        relationship = _safe_load_json_dict(progress.relationship_modifiers_json)
        growth_summary = (
            f"battle_exp={int(growth.get('battle_exp_points', 0) or 0)}, "
            f"battles={int(growth.get('battle_count', 0) or 0)}"
        )
        trust = float(relationship.get("trust_in_leader", 0.0) or 0.0)
        relationship_summary = f"trust_in_leader={round(trust, 2)}"
        items.append(
            {
                "entity_id": progress.entity_id,
                "display_name": progress.display_name,
                "growth_summary": growth_summary,
                "relationship_summary": relationship_summary,
            }
        )
    return items


def build_gathering_summary(db: Session, *, world_id: int) -> tuple[str, str]:
    context = get_expedition_context(db, world_id=world_id)
    gathered_materials = dict(context.get("gathered_materials", {}) or {})
    if not gathered_materials:
        return "{}", "まだ拠点へ持ち帰った採集素材はない。"

    parts = []
    for key, value in gathered_materials.items():
        label = "鉄鉱石" if key == "iron_ore" else ("魔石片" if key == "mana_shard" else key)
        parts.append(f"{label} x{int(value)}")
    return serialize_gathered_materials(context), " / ".join(parts)


def build_economy_snapshot(state: WorldState) -> dict[str, int | str]:
    return {
        "gold": int(state.gold),
        "tax_debt": int(state.tax_debt),
        "meal_stock": int(state.meal_stock),
        "housing_tier": str(state.housing_tier),
    }


def list_economy_previews(world: World, state: WorldState) -> list[dict[str, str | int]]:
    travel_min_cost = min(TRAVEL_COST_BY_DESTINATION.values()) if TRAVEL_COST_BY_DESTINATION else 0
    return [
        {
            "action_key": "rest",
            "label": "休憩 / 宿泊",
            "estimated_cost": int(REST_COST_BY_LOCATION.get(world.current_location, 4)),
            "summary": "安全に休むほど出費は増えるが、安定して立て直せる。",
        },
        {
            "action_key": "meal",
            "label": "食事",
            "estimated_cost": int(MEAL_COST),
            "summary": "安価な回復と生活感のある小さな支出。",
        },
        {
            "action_key": "travel",
            "label": "移動費",
            "estimated_cost": int(travel_min_cost),
            "summary": "荷や護衛を伴う移動には細かな費用がかかる。",
        },
        {
            "action_key": "pay_tax",
            "label": "税金支払い",
            "estimated_cost": min(int(state.tax_debt), TAX_PAYMENT_UNIT),
            "summary": "滞納を減らして評判悪化を抑える。後回しにすると圧迫要因になる。",
        },
        {
            "action_key": "gamble",
            "label": "賭け事",
            "estimated_cost": int(GAMBLE_STAKE),
            "summary": "短期で増えることもあるが、安定資金には向かない。",
        },
        {
            "action_key": "housing_upgrade",
            "label": "住居拡張",
            "estimated_cost": int(HOUSING_UPGRADE_CHAIN.get(str(state.housing_tier), {}).get("cost", 0) or 0),
            "summary": "住環境を整え、長期行動の基盤を安定させる。",
        },
    ]


def _ensure_affordable(state: WorldState, cost: int) -> None:
    if int(state.gold) < int(cost):
        raise ValueError("insufficient gold")


def _apply_gold_change(state: WorldState, delta: int) -> None:
    state.gold = max(0, int(state.gold) + int(delta))


def _read_hub_resource_context(db: Session, *, world_id: int) -> dict[str, Any]:
    state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(state)
    hub = context.get("hub", {})
    if not isinstance(hub, dict):
        hub = {}
    crafted_supplies = hub.get("crafted_supplies", {})
    if not isinstance(crafted_supplies, dict):
        crafted_supplies = {}
    material_credit = int(hub.get("material_credit", 0) or 0)
    purchased_equipment = hub.get("purchased_equipment", [])
    if not isinstance(purchased_equipment, list):
        purchased_equipment = []
    return {
        "crafted_supplies": crafted_supplies,
        "material_credit": material_credit,
        "purchased_equipment": [str(item) for item in purchased_equipment],
    }


def _write_hub_resource_context(
    db: Session,
    *,
    world_id: int,
    crafted_supplies: dict[str, int],
    material_credit: int,
    purchased_equipment: list[str] | None = None,
) -> dict[str, Any]:
    state = get_or_create_campaign_state(db, world_id)
    context = read_phase_context(state)
    current_hub = context.get("hub", {})
    if not isinstance(current_hub, dict):
        current_hub = {}
    current_hub.update({
        "crafted_supplies": dict(crafted_supplies),
        "material_credit": int(material_credit),
    })
    if purchased_equipment is not None:
        current_hub["purchased_equipment"] = [str(item) for item in purchased_equipment]
    context["hub"] = current_hub
    write_phase_context(state, context)
    db.add(state)
    db.flush()
    return {
        "crafted_supplies": dict(crafted_supplies),
        "material_credit": int(material_credit),
        "purchased_equipment": list(current_hub.get("purchased_equipment", []) or []),
    }


def build_hub_resource_summary(
    db: Session,
    *,
    world_id: int,
) -> tuple[str, int, str]:
    context = _read_hub_resource_context(db, world_id=world_id)
    return (
        json.dumps(context["crafted_supplies"], ensure_ascii=False),
        int(context["material_credit"]),
        json.dumps(context["purchased_equipment"], ensure_ascii=False),
    )


def build_purchased_equipment_summary(db: Session, *, world_id: int) -> list[dict[str, Any]]:
    context = _read_hub_resource_context(db, world_id=world_id)
    items: list[dict[str, Any]] = []
    for equipment_key in list(context.get("purchased_equipment", []) or []):
        equipment = get_equipment(str(equipment_key))
        if not equipment:
            continue
        items.append(
            {
                "equipment_key": equipment.equipment_key,
                "name": equipment.name,
                "slot_type": equipment.slot_type,
                "rarity": equipment.rarity,
                "summary": equipment.flavor_text or "生成装備として拠点に保管されている。",
            }
        )
    return items


def get_hub_resource_snapshot(db: Session, *, world_id: int) -> dict[str, Any]:
    return _read_hub_resource_context(db, world_id=world_id)


def list_craft_previews(db: Session, *, world_id: int) -> list[dict[str, str | bool]]:
    expedition = get_expedition_context(db, world_id=world_id)
    materials = dict(expedition.get("gathered_materials", {}) or {})
    state = get_or_create_campaign_state(db, world_id)
    world_state = db.query(WorldState).filter(WorldState.world_id == world_id).first()
    items = []
    for recipe_key, recipe in CRAFT_RECIPES.items():
        cost = dict(recipe["cost"])
        gold_cost = 6 if recipe_key == "field_repair_kit" else 8
        craftable = all(int(materials.get(key, 0) or 0) >= int(value) for key, value in cost.items())
        if world_state and int(world_state.gold) < gold_cost:
            craftable = False
        cost_parts = []
        for key, value in cost.items():
            label = "鉄鉱石" if key == "iron_ore" else ("魔石片" if key == "mana_shard" else key)
            cost_parts.append(f"{label} x{int(value)}")
        cost_parts.append(f"金貨 x{gold_cost}")
        items.append(
            {
                "recipe_key": recipe_key,
                "label": str(recipe["label"]),
                "summary": str(recipe["summary"]),
                "craftable": craftable,
                "cost_summary": " / ".join(cost_parts),
            }
        )
    return items


def list_market_offers(db: Session, *, world: World, state: WorldState) -> list[dict[str, Any]]:
    offers = build_market_offers(world_seed=int(world.seed), security_score=int(state.security_score), count=4)
    hub_resources = _read_hub_resource_context(db, world_id=world.world_id)
    purchased = set(str(item) for item in hub_resources.get("purchased_equipment", []) or [])
    items: list[dict[str, Any]] = []
    for offer in offers:
        item = dict(offer)
        item["purchased"] = str(item["offer_key"]) in purchased
        items.append(item)
    return items


def build_housing_preview(state: WorldState) -> dict[str, Any] | None:
    current_tier = str(state.housing_tier)
    if current_tier not in HOUSING_UPGRADE_CHAIN:
        return None
    config = dict(HOUSING_UPGRADE_CHAIN[current_tier])
    return {
        "housing_tier": current_tier,
        "next_housing_tier": str(config["next_tier"]),
        "upgrade_cost": int(config["cost"]),
        "available": int(state.gold) >= int(config["cost"]),
        "summary": str(config["summary"]),
    }


def list_sell_previews(db: Session, *, world_id: int) -> list[dict[str, str | int]]:
    expedition = get_expedition_context(db, world_id=world_id)
    materials = dict(expedition.get("gathered_materials", {}) or {})
    items = []
    for key, quantity in materials.items():
        qty = int(quantity or 0)
        if qty <= 0:
            continue
        label = "鉄鉱石" if key == "iron_ore" else ("魔石片" if key == "mana_shard" else key)
        items.append(
            {
                "material_key": key,
                "label": label,
                "quantity": qty,
                "estimated_credit": qty * int(MATERIAL_CREDIT_VALUES.get(key, 1)),
            }
        )
    return items


def execute_hub_craft(
    db: Session,
    *,
    world: World,
    recipe_key: str,
) -> tuple[str, str]:
    if recipe_key not in CRAFT_RECIPES:
        raise ValueError("unknown recipe")

    expedition = get_expedition_context(db, world_id=world.world_id)
    materials = dict(expedition.get("gathered_materials", {}) or {})
    recipe = CRAFT_RECIPES[recipe_key]
    cost = dict(recipe["cost"])
    state = db.query(WorldState).filter(WorldState.world_id == world.world_id).first()
    if not state:
        raise ValueError("world state not found")
    gold_cost = 6 if recipe_key == "field_repair_kit" else 8
    _ensure_affordable(state, gold_cost)
    for key, value in cost.items():
        if int(materials.get(key, 0) or 0) < int(value):
            raise ValueError("insufficient materials")

    for key, value in cost.items():
        materials[key] = int(materials.get(key, 0) or 0) - int(value)
        if materials[key] <= 0:
            materials.pop(key, None)

    expedition = get_expedition_context(db, world_id=world.world_id)
    from app.services.expedition_service import set_expedition_context

    set_expedition_context(
        db,
        world_id=world.world_id,
        progress_stage=int(expedition["progress_stage"]),
        supply_pressure=int(expedition["supply_pressure"]),
        danger_level=str(expedition["danger_level"]),
        gathered_materials=materials,
    )

    hub_resources = _read_hub_resource_context(db, world_id=world.world_id)
    crafted = dict(hub_resources["crafted_supplies"])
    for key, value in dict(recipe["yield"]).items():
        crafted[key] = int(crafted.get(key, 0) or 0) + int(value)
    _write_hub_resource_context(
        db,
        world_id=world.world_id,
        crafted_supplies=crafted,
        material_credit=int(hub_resources["material_credit"]),
        purchased_equipment=list(hub_resources["purchased_equipment"]),
    )
    _apply_gold_change(state, -gold_cost)

    summary = f"{recipe['label']}を作成し、採集素材と金貨 {gold_cost} を次の備えへ変えた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 簡易クラフト",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "craft"


def execute_hub_sell_materials(
    db: Session,
    *,
    world: World,
) -> tuple[str, str]:
    expedition = get_expedition_context(db, world_id=world.world_id)
    materials = dict(expedition.get("gathered_materials", {}) or {})
    if not materials:
        raise ValueError("no materials to sell")

    earned_credit = 0
    for key, quantity in materials.items():
        earned_credit += int(quantity or 0) * int(MATERIAL_CREDIT_VALUES.get(key, 1))

    from app.services.expedition_service import set_expedition_context

    set_expedition_context(
        db,
        world_id=world.world_id,
        progress_stage=int(expedition["progress_stage"]),
        supply_pressure=int(expedition["supply_pressure"]),
        danger_level=str(expedition["danger_level"]),
        gathered_materials={},
    )

    hub_resources = _read_hub_resource_context(db, world_id=world.world_id)
    _write_hub_resource_context(
        db,
        world_id=world.world_id,
        crafted_supplies=dict(hub_resources["crafted_supplies"]),
        material_credit=int(hub_resources["material_credit"]) + earned_credit,
        purchased_equipment=list(hub_resources["purchased_equipment"]),
    )

    summary = f"採集素材を売却し、素材換金価値 {earned_credit} を拠点資金へ変えた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 素材売却",
            body=summary,
        )
    )
    db.flush()
    return summary, "sell"


def execute_hub_rest(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> tuple[str, str]:
    rest_cost = int(REST_COST_BY_LOCATION.get(world.current_location, 4))
    _ensure_affordable(state, rest_cost)
    _apply_gold_change(state, -rest_cost)
    state.demon_score = max(0, state.demon_score - 1)
    if str(state.housing_tier) == "room":
        state.security_score = min(100, int(state.security_score) + 1)
    elif str(state.housing_tier) == "house":
        state.security_score = min(100, int(state.security_score) + 2)
    apply_tendency_delta(
        db,
        world_id=world.world_id,
        reason="hub:rest",
        deltas={"cautious": 1, "protective": 1},
    )
    summary = f"拠点で休息を取り、金貨 {rest_cost} を払って次の行動に備えて体勢を整えた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 休息",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "recovery"


def execute_hub_travel(
    db: Session,
    *,
    world: World,
    target_location: str,
) -> tuple[str, str]:
    next_location = DESTINATION_LOCATION_MAP.get(target_location)
    if not next_location:
        raise ValueError("unknown destination")
    state = db.query(WorldState).filter(WorldState.world_id == world.world_id).first()
    if not state:
        raise ValueError("world state not found")
    travel_cost = int(TRAVEL_COST_BY_DESTINATION.get(target_location, 1))
    _ensure_affordable(state, travel_cost)
    _apply_gold_change(state, -travel_cost)

    world.current_location = next_location
    move_delta = {"bold": 1}
    if target_location == "north_mine":
        move_delta["cautious"] = 1
    apply_tendency_delta(
        db,
        world_id=world.world_id,
        reason="hub:travel",
        deltas=move_delta,
    )
    summary = f"金貨 {travel_cost} を払って{next_location}へ移動し、周囲の空気を確かめながら次の行動に備えた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 出発",
            body=summary,
        )
    )
    db.add(state)
    db.add(world)
    db.flush()
    return summary, "movement"


def execute_hub_meal(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> tuple[str, str]:
    _ensure_affordable(state, MEAL_COST)
    _apply_gold_change(state, -MEAL_COST)
    state.meal_stock = max(0, int(state.meal_stock) + 1)
    state.demon_score = max(0, state.demon_score - 1)
    summary = f"温かい食事に金貨 {MEAL_COST} を使い、張りつめていた気分を少し和らげた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 食事",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "meal"


def execute_hub_gamble(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> tuple[str, str]:
    _ensure_affordable(state, GAMBLE_STAKE)
    base_roll = (int(world.seed) + int(state.quest_progress) + int(state.gold) + int(state.security_score)) % 5
    _apply_gold_change(state, -GAMBLE_STAKE)
    result_delta = [-5, -2, 0, 4, 8][base_roll]
    _apply_gold_change(state, result_delta)
    if result_delta > 0:
        summary = f"賭け事に金貨 {GAMBLE_STAKE} を投じ、差し引き {result_delta} 枚の利益を得た。"
        result_type = "gamble_win"
    elif result_delta == 0:
        summary = f"賭け事に金貨 {GAMBLE_STAKE} を使ったが、収支はほぼ変わらなかった。"
        result_type = "gamble_even"
    else:
        summary = f"賭け事に金貨 {GAMBLE_STAKE} を投じたが、さらに {-result_delta} 枚を失った。"
        result_type = "gamble_loss"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 賭け事",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, result_type


def execute_hub_pay_tax(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> tuple[str, str]:
    tax_payment = min(int(state.tax_debt), TAX_PAYMENT_UNIT)
    if tax_payment <= 0:
        raise ValueError("no tax debt")
    _ensure_affordable(state, tax_payment)
    _apply_gold_change(state, -tax_payment)
    state.tax_debt = max(0, int(state.tax_debt) - tax_payment)
    summary = f"税金として金貨 {tax_payment} を支払い、滞納を少し減らした。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 納税",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "tax"


def execute_hub_buy_market_offer(
    db: Session,
    *,
    world: World,
    state: WorldState,
    offer_key: str,
) -> tuple[str, str]:
    offer = get_market_offer_by_key(world_seed=int(world.seed), security_score=int(state.security_score), offer_key=str(offer_key))
    if not offer:
        raise ValueError("unknown market offer")
    hub_resources = _read_hub_resource_context(db, world_id=world.world_id)
    purchased_equipment = list(hub_resources["purchased_equipment"])
    if str(offer_key) in purchased_equipment:
        raise ValueError("market offer already purchased")
    price = int(offer.get("price_gold", 0) or 0)
    _ensure_affordable(state, price)
    register_market_equipment(offer)
    purchased_equipment.append(str(offer_key))
    _write_hub_resource_context(
        db,
        world_id=world.world_id,
        crafted_supplies=dict(hub_resources["crafted_supplies"]),
        material_credit=int(hub_resources["material_credit"]),
        purchased_equipment=purchased_equipment,
    )
    _apply_gold_change(state, -price)
    summary = f"{offer['name']}を金貨 {price} で入手し、次の戦いや探索に備える装備を整えた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 装備購入",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "market_purchase"


def execute_hub_upgrade_housing(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> tuple[str, str]:
    current_tier = str(state.housing_tier)
    config = HOUSING_UPGRADE_CHAIN.get(current_tier)
    if not config:
        raise ValueError("housing already maximized")
    cost = int(config["cost"])
    _ensure_affordable(state, cost)
    _apply_gold_change(state, -cost)
    state.housing_tier = str(config["next_tier"])
    state.security_score = min(100, int(state.security_score) + 2)
    state.tax_debt = max(0, int(state.tax_debt) - 2)
    summary = f"住居を{state.housing_tier}へ整え、金貨 {cost} を長期拠点の安定へ投じた。"
    db.add(
        Log(
            world_id=world.world_id,
            log_type="hub",
            title="拠点: 住居拡張",
            body=summary,
        )
    )
    db.add(state)
    db.flush()
    return summary, "housing_upgrade"
