from __future__ import annotations

import json
import random

from sqlalchemy.orm import Session

from app.models.world import World
from app.models.world_faction_state import WorldFactionState
from app.services.campaign_phase_service import get_or_create_campaign_state
from app.services.world_progress_service import get_or_create_world_state, get_security_band

FACTION_CATEGORY_TEMPLATES = [
    ("guild", ["暁の冒険者組合", "灰鐘の探索者会", "風刃の依頼人組合"]),
    ("church", ["白枝の癒祷会", "六灯の祈り手", "巡礼の鐘教会"]),
    ("merchant", ["青銅秤商会", "月舟交易組", "琥珀路の商人会"]),
    ("militia", ["北門守備隊", "霧辺の巡邏隊", "村外縁警備団"]),
]


def _safe_dump_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)


def ensure_world_factions(db: Session, *, world: World) -> list[WorldFactionState]:
    existing = (
        db.query(WorldFactionState)
        .filter(WorldFactionState.world_id == world.world_id)
        .order_by(WorldFactionState.faction_state_id.asc())
        .all()
    )
    if existing:
        return existing

    rng = random.Random(int(world.seed) + int(world.world_id) * 97)
    created: list[WorldFactionState] = []
    for index, (category, names) in enumerate(FACTION_CATEGORY_TEMPLATES):
        faction = WorldFactionState(
            world_id=world.world_id,
            faction_key=f"{category}_{index+1:03d}",
            display_name=str(names[rng.randrange(len(names))]),
            category=category,
            influence_score=round(rng.uniform(0.35, 0.8), 3),
            power_score=round(rng.uniform(0.3, 0.75), 3),
            cohesion_score=round(rng.uniform(0.35, 0.85), 3),
            tension_score=round(rng.uniform(0.05, 0.35), 3),
            stance_label=("moral" if category == "church" else "profit" if category == "merchant" else "security" if category == "militia" else "opportunity"),
            notes_json=_safe_dump_json({"seed_origin": int(world.seed), "category": category}),
            last_incident_hint="",
        )
        db.add(faction)
        created.append(faction)
    db.flush()
    return created


def _build_faction_incident_hint(db: Session, *, faction: WorldFactionState, world: World) -> str:
    world_state = get_or_create_world_state(db, world.world_id)
    campaign_state = get_or_create_campaign_state(db, world.world_id)
    security_band = get_security_band(world_state.security_score)
    day_no = int(campaign_state.day_no)

    if security_band in {"unstable", "lawless"} and faction.category == "militia":
        return f"{faction.display_name}は盗賊対策を巡って過重負担を抱え、離脱者が出かねない。"
    if security_band in {"unstable", "lawless"} and faction.category == "merchant":
        return f"{faction.display_name}は護衛費の高騰で他派閥との合併交渉を進めている。"
    if world_state.faction_score >= 24 and faction.category == "church":
        return f"{faction.display_name}では王国寄りか民衆寄りかを巡って教義論争が強まっている。"
    if faction.tension_score >= 0.5:
        return f"{faction.display_name}では要人暗殺の疑惑が広がり、内部の粛清や離散が噂されている。"
    if faction.cohesion_score <= 0.3:
        return f"{faction.display_name}は内部の足並みが乱れ、分裂や吸収合併の火種を抱えている。"
    if faction.category == "guild" and day_no % 3 == 0:
        return f"{faction.display_name}は新しい依頼の配分を巡り、商会や守備隊と神経質な駆け引きを続けている。"
    if faction.category == "church":
        return f"{faction.display_name}は街角で説教を重ね、信徒を巡って他宗派と静かな競合を起こしている。"
    return f"{faction.display_name}は今のところ表立った破綻はないが、水面下では勢力争いが続いている。"


def list_world_factions(db: Session, *, world: World, limit: int = 4) -> list[dict[str, object]]:
    factions = ensure_world_factions(db, world=world)
    items: list[dict[str, object]] = []
    for faction in factions[:limit]:
        incident_hint = _build_faction_incident_hint(db, faction=faction, world=world)
        faction.last_incident_hint = incident_hint
        db.add(faction)
        items.append(
            {
                "faction_key": faction.faction_key,
                "display_name": faction.display_name,
                "category": faction.category,
                "influence_score": round(float(faction.influence_score), 3),
                "power_score": round(float(faction.power_score), 3),
                "cohesion_score": round(float(faction.cohesion_score), 3),
                "tension_score": round(float(faction.tension_score), 3),
                "stance_label": faction.stance_label,
                "incident_hint": incident_hint,
            }
        )
    db.flush()
    return items


def list_faction_incident_hints(db: Session, *, world: World, limit: int = 3) -> list[str]:
    return [str(item["incident_hint"]) for item in list_world_factions(db, world=world, limit=limit)]
