from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.quest import Quest
from app.models.world import World
from app.services.expedition_service import get_expedition_context, serialize_gathered_materials
from app.services.faction_service import list_world_factions
from app.services.generation_content_service import build_authority_candidates, build_blessing_offers
from app.services.hub_service import build_purchased_equipment_summary
from app.services.relation_graph_service import list_top_relation_summaries
from app.services.relation_story_service import list_relation_story_quests
from app.services.world_progress_service import build_security_rumors, get_or_create_world_state, get_security_band


def list_recent_chronicle_logs(db: Session, *, world_id: int, limit: int = 5) -> list[dict[str, str]]:
    logs = (
        db.query(Log)
        .filter(Log.world_id == world_id)
        .order_by(Log.log_id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "log_type": log.log_type,
            "title": log.title,
            "body": log.body,
        }
        for log in logs
    ]


def list_active_quests(db: Session, *, world_id: int, limit: int = 5) -> list[dict[str, str | int]]:
    quests = (
        db.query(Quest)
        .filter(Quest.world_id == world_id)
        .order_by(Quest.quest_row_id.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "quest_id": quest.quest_id,
            "title": quest.title,
            "status": quest.status,
            "progress": quest.progress,
        }
        for quest in quests
    ]


def build_chronicle_summary(db: Session, *, world: World) -> str:
    state = get_or_create_world_state(db, world.world_id)
    progress = state.quest_progress
    pressure = max(state.dungeon_score, state.faction_score, state.demon_score)
    if state.security_score <= 30:
        return "戦争と政争のひずみが治安崩壊となって表れ、盗賊討伐や護衛依頼が物語の前面へせり上がっている。"
    if state.security_score <= 45:
        return "村と街道の治安は悪化し、盗賊や強盗への対処が主線と並ぶ火急の課題になりつつある。"
    if progress >= 5:
        return "北坑道の異変はひとまず決着し、その余波が村や周辺地域の記録として残り始めている。"
    if pressure >= 50:
        return "世界はまだ大きな決着を迎えていないが、異変の波紋は日常の奥で確実に広がっている。"
    return "目立った破局は起きていないが、小さな選択の積み重ねが次の章の土台になりつつある。"


def build_inheritance_options(db: Session, *, world: World) -> list[dict[str, str]]:
    state = get_or_create_world_state(db, world.world_id)
    options = [
        {
            "inheritance_key": "persistent_cheat",
            "label": "義認権能の継承",
            "summary": "創造神から与えられた中核チートを次周回へ残す。",
        },
        {
            "inheritance_key": "conditional_blessing",
            "label": "恩寵の持ち越し",
            "summary": "存続した神格や信仰による恩寵だけを条件付きで継承する。",
        },
    ]
    if state.quest_progress >= 3:
        options.append(
            {
                "inheritance_key": "loop_bonus_cheat",
                "label": "追加チート候補",
                "summary": "進行実績に応じ、強くてニューゲーム時の追加チート候補を開く。",
            }
        )
    else:
        options.append(
            {
                "inheritance_key": "loop_bonus_cheat_locked",
                "label": "追加チート候補",
                "summary": "物語の進行が深まると、強くてニューゲーム用の追加チート候補が解放される。",
            }
        )
    return options


def build_materials_legacy_summary(db: Session, *, world: World) -> tuple[str, str]:
    context = get_expedition_context(db, world_id=world.world_id)
    gathered_materials = dict(context.get("gathered_materials", {}) or {})
    if not gathered_materials:
        return "{}", "採集した鉱石や魔石はまだ少なく、次代へ残る資産にはなっていない。"

    parts = []
    if int(gathered_materials.get("iron_ore", 0) or 0) > 0:
        parts.append("鍛冶素材として使える鉄鉱石が蓄積している")
    if int(gathered_materials.get("mana_shard", 0) or 0) > 0:
        parts.append("魔石片が蓄積し、将来の触媒や継承資産に繋げやすい")
    if not parts:
        parts.append("採集素材はあるが、まだ物語上の意味づけは薄い")
    return serialize_gathered_materials(context), "。".join(parts) + "。"


def build_security_outlook(db: Session, *, world: World) -> tuple[int, str, str]:
    state = get_or_create_world_state(db, world.world_id)
    band = get_security_band(state.security_score)
    rumors = build_security_rumors(state)
    return state.security_score, band, rumors[0] if rumors else "治安に大きな変化は見られない。"


def build_relation_legacy_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return list_top_relation_summaries(db, world_id=world.world_id)


def build_relation_story_quest_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return list_relation_story_quests(db, world_id=world.world_id)


def build_faction_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return list_world_factions(db, world=world)


def build_purchased_equipment_legacy_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return build_purchased_equipment_summary(db, world_id=world.world_id)


def build_blessing_offer_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return build_blessing_offers(world_seed=int(world.seed), count=3)


def build_authority_candidate_summary(db: Session, *, world: World) -> list[dict[str, object]]:
    return build_authority_candidates(world_seed=int(world.seed), count=3)
