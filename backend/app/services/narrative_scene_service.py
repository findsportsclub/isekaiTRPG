from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.world import World
from app.models.world_state import WorldState
from app.services.campaign_phase_service import (
    get_or_create_campaign_state,
    get_phase_metadata,
    read_narrative_state,
)
from app.services.relationship_service import list_relationship_hints
from app.services.relation_graph_service import list_relation_story_hints
from app.services.tendency_service import (
    build_tendency_hint_list,
    get_or_create_tendency_state,
    read_tendency_scores,
)
from app.services.world_progress_service import get_or_create_world_state
import json

TIME_SLOT_LABELS = {
    "MORNING": "朝",
    "DAY": "昼",
    "EVENING": "夕方",
    "NIGHT": "夜",
}

LOCATION_SCENE_BASE: dict[str, dict[str, str]] = {
    "はじまりの村": {
        "title": "村の息づかい",
        "base": "村の空気はまだ柔らかいが、北へ向く視線には落ち着かない色が混じっている。",
        "crowd": "広場では何人かが足を止め、噂を交わしながらも声量を抑えていた。",
    },
    "村の入口": {
        "title": "街道の境目",
        "base": "村の入口には出入りする者の気配がある一方で、外へ伸びる道はどこか張りつめて見えた。",
        "crowd": "見張り台の近くでは、街道を見送る目が以前より鋭くなっている。",
    },
    "北坑道前": {
        "title": "坑道前の重み",
        "base": "坑道前の空気は冷え、入口へ近づくほど人の気配が薄れていく。",
        "crowd": "遠巻きに様子を見る者たちは、奥から流れる空気に不安を隠しきれていない。",
    },
    "宿屋": {
        "title": "宿のひそ声",
        "base": "宿の灯りは温かいが、旅人たちの会話には今夜も北の話が混じる。",
        "crowd": "卓を囲む者たちは笑顔を作っていても、霧や失踪の噂になると自然と身を寄せた。",
    },
}


def _crisis_phrase(state: WorldState) -> str:
    pressure = max(state.dungeon_score, state.faction_score, state.demon_score)
    if pressure >= 60:
        return "場のどこかに切迫した気配が張りついており、平穏を装う余裕はほとんどない。"
    if pressure >= 30:
        return "表面上は日常が保たれていても、誰もが何かの兆しを感じ取っている。"
    return "まだ大崩れはしていないが、不安の芽は確かに育ち始めている。"


def _phase_phrase(phase_key: str) -> str:
    mapping = {
        "HUB": "今は次の動きに備えて息を整える時間だ。",
        "INTERACTION": "言葉の選び方ひとつで、今後の信頼も警戒も変わりうる。",
        "INVESTIGATION": "小さな違和感を見逃さないことが、次の一歩を決める。",
        "EXPEDITION": "安全圏を離れた以上、進むたびに判断の重みが増していく。",
        "BATTLE": "躊躇よりも先に、誰を守り何を崩すかを決めねばならない。",
        "WAR": "一つの勝敗ではなく、どこへ力を注ぐかが戦局そのものを動かす。",
        "WORLD": "個々の出来事はやがて噂や記録となり、次の時代への伏線になる。",
    }
    return mapping.get(phase_key, "")


def build_campaign_scene_payload(db: Session, world_id: int) -> dict[str, str | int]:
    world = db.query(World).filter(World.world_id == world_id).first()
    if not world:
        raise ValueError("world not found")

    campaign_state = get_or_create_campaign_state(db, world_id)
    world_state = get_or_create_world_state(db, world_id)
    tendency_state = get_or_create_tendency_state(db, world_id=world_id)
    narrative_state = read_narrative_state(campaign_state)
    phase_key = str(campaign_state.current_phase or "HUB").upper().strip()
    phase_meta = get_phase_metadata(phase_key)

    location_data = LOCATION_SCENE_BASE.get(
        world.current_location,
        {
            "title": "旅のひと区切り",
            "base": "見慣れぬ土地でも、空気の重さは今の世界が何を抱えているかを語っている。",
            "crowd": "行き交う者の足取りや視線には、その土地なりの緊張が滲んでいた。",
        },
    )

    time_label = TIME_SLOT_LABELS.get(campaign_state.time_slot, campaign_state.time_slot)
    body = " ".join(
        [
            f"{time_label}の{world.current_location}。{location_data['base']}",
            location_data["crowd"],
            _crisis_phrase(world_state),
            _phase_phrase(phase_key),
        ]
    ).strip()

    tendency_hints = build_tendency_hint_list(read_tendency_scores(tendency_state))
    relationship_hints = list_relationship_hints(db, world_id=world_id)
    relation_story_hints = list_relation_story_hints(db, world_id=world_id)

    return {
        "world_id": world_id,
        "current_phase": phase_key,
        "current_phase_label": phase_meta["label"],
        "day_no": campaign_state.day_no,
        "time_slot": campaign_state.time_slot,
        "scene_title": location_data["title"],
        "scene_body": body,
        "tone": str(narrative_state.get("tone", "calm")),
        "weight": str(narrative_state.get("weight", "normal")),
        "protagonist_tendency_hints": tendency_hints,
        "active_relationship_hints_json": json.dumps(
            {
                "reactions": relationship_hints,
                "story_hints": relation_story_hints,
            },
            ensure_ascii=False,
        ),
    }
