from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.quest import Quest
from app.models.world import World
from app.models.world_state import WorldState
from app.services.tendency_service import (
    apply_tendency_delta,
    get_or_create_tendency_state,
    get_primary_tendency,
    read_tendency_scores,
)
from app.services.relation_graph_service import (
    RELATION_TARGET_DEFAULTS,
    apply_relation_observation,
    build_relation_edge_summary,
)
from app.services.relation_story_service import sync_relation_story_quest
from app.services.world_progress_service import (
    apply_world_quest_completion_rules,
    sync_security_side_quest,
)


def list_investigation_options(world: World) -> list[dict[str, str]]:
    if world.current_location == "はじまりの村":
        return [{"option_key": "inspect", "label": "掲示板を調べる", "summary": "村の依頼や噂を拾う。"}]
    if world.current_location == "村の入口":
        return [{"option_key": "inspect", "label": "地面を調べる", "summary": "新しい足跡や痕跡を追う。"}]
    if world.current_location == "北坑道前":
        return [{"option_key": "inspect", "label": "坑道入口を調べる", "summary": "傷跡や裂け目を観察する。"}]
    if world.current_location == "宿屋":
        return [{"option_key": "inspect", "label": "宿の荷を調べる", "summary": "地図や旅人の残した手がかりを探す。"}]
    return [{"option_key": "inspect", "label": "周囲を調べる", "summary": "その場に残された違和感を探る。"}]


def build_investigation_option_suggestions(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> dict[str, object]:
    tendency_state = get_or_create_tendency_state(db, world_id=world.world_id)
    scores = read_tendency_scores(tendency_state)
    primary = get_primary_tendency(scores)

    recommended_option_key = "inspect"
    if state.quest_progress >= 3:
        reason = "主線が進んでいるので、さらに手がかりを固める価値が高い。"
    elif primary in {"curious", "cautious"}:
        reason = "現在の傾向と相性がよく、調査を重ねるほど次の判断材料が増える。"
    elif world.current_location == "北坑道前":
        reason = "危険地帯へ踏み込む前に、入口で拾える違和感を先に押さえておきたい。"
    else:
        reason = "現段階では周囲を調べるのが最も損失が少なく、情報効率が高い。"

    options = []
    for item in list_investigation_options(world):
        options.append(
            {
                **item,
                "recommended": item["option_key"] == recommended_option_key,
                "reason": reason if item["option_key"] == recommended_option_key else "現地の追加情報を拾うための標準的な調査行動。",
            }
        )

    return {
        "recommended_option_key": recommended_option_key,
        "options": options,
    }


def _resolve_investigation_relation_target(world: World, state: WorldState) -> str | None:
    if world.current_location == "村の入口":
        return "npc_003"
    if world.current_location == "宿屋":
        return "npc_002"
    if world.current_location == "北坑道前":
        return "npc_004"
    if world.current_location == "はじまりの村" and state.security_score <= 45:
        return "npc_001"
    return None


def build_investigation_relation_summary(
    db: Session,
    *,
    world: World,
    state: WorldState,
) -> dict[str, object] | None:
    target_key = _resolve_investigation_relation_target(world, state)
    if not target_key:
        return None
    return build_relation_edge_summary(
        db,
        world_id=world.world_id,
        actor_key="hero",
        target_key=target_key,
        display_name=str(RELATION_TARGET_DEFAULTS.get(target_key, {}).get("display_name", target_key)),
    )


def execute_investigation(
    db: Session,
    *,
    world: World,
    state: WorldState,
    main_quest: Quest | None,
    side_quest_001: Quest | None,
    option_key: str,
) -> tuple[str, str]:
    if option_key != "inspect":
        raise ValueError(f"unsupported investigation option: {option_key}")

    if world.current_location == "はじまりの村":
        if state.security_score <= 45:
            summary = "掲示板には北坑道の噂に混じって、『街道の盗賊を討て』という新しい討伐依頼が目立っていた。"
            result_type = "security"
            state.faction_score += 1
            state.quest_progress += 1
            state.main_event_title = "街道治安の悪化"
            state.main_event_state = "ACTIVE"
            if main_quest:
                main_quest.progress += 1
        else:
            summary = "掲示板を調べると、北坑道の見回り依頼が貼られていた。"
            result_type = "discovery"
            state.dungeon_score += 1
            state.quest_progress += 1
            state.main_event_title = "北坑道の見回り依頼"
            state.main_event_state = "ACTIVE"
            if main_quest:
                main_quest.progress += 1
    elif world.current_location == "村の入口":
        if state.security_score <= 45:
            security_quest = sync_security_side_quest(db, world_id=world.world_id, state=state)
            summary = "地面を調べると、荷を引きずった跡と複数の足跡が街道脇へ逸れていた。盗賊が待ち伏せに使う道筋らしい。"
            result_type = "security"
            state.security_score = min(100, state.security_score + 1)
            if security_quest and security_quest.status != "CLEARED":
                security_quest.progress += 1
                db.add(security_quest)
            edge = apply_relation_observation(
                db,
                world_id=world.world_id,
                target_key="npc_003",
                display_name=str(RELATION_TARGET_DEFAULTS.get("npc_003", {}).get("display_name", "npc_003")),
                reason="investigation:street_watch",
                trust_delta=0.03,
                respect_delta=0.05,
                loyalty_delta=0.02,
            )
            sync_relation_story_quest(db, edge=edge)
        else:
            summary = "地面を調べると、村の外へ向かう新しい足跡がいくつも見つかった。"
            result_type = "discovery"
            state.dungeon_score += 2
            state.quest_progress += 1
            state.main_event_title = "街道に残された足跡"
            state.main_event_state = "ACTIVE"
            if main_quest:
                main_quest.progress += 1
            edge = apply_relation_observation(
                db,
                world_id=world.world_id,
                target_key="npc_003",
                display_name=str(RELATION_TARGET_DEFAULTS.get("npc_003", {}).get("display_name", "npc_003")),
                reason="investigation:street_trace",
                trust_delta=0.02,
                respect_delta=0.04,
            )
            sync_relation_story_quest(db, edge=edge)
    elif world.current_location == "北坑道前":
        summary = "坑道の入口には、爪で削ったような深い傷跡が残っていた。さらに壁際に、不自然に風が流れ込む裂け目を見つけた。"
        result_type = "discovery"
        state.dungeon_score += 3
        state.quest_progress += 2
        state.main_event_title = "坑道入口の異変"
        state.main_event_state = "ACTIVE"
        if main_quest:
            main_quest.progress += 2
        if side_quest_001 and side_quest_001.status != "CLEARED":
            side_quest_001.progress += 1
            if side_quest_001.progress >= 2:
                side_quest_001.status = "CLEARED"
        edge = apply_relation_observation(
            db,
            world_id=world.world_id,
            target_key="npc_004",
            display_name=str(RELATION_TARGET_DEFAULTS.get("npc_004", {}).get("display_name", "npc_004")),
            reason="investigation:mine_anomaly",
            trust_delta=0.01,
            respect_delta=0.05,
        )
        sync_relation_story_quest(db, edge=edge)
    elif world.current_location == "宿屋":
        summary = "宿の片隅に置かれた荷の中に、坑道の地図の切れ端を見つけた。未探索の横穴があるようだ。"
        result_type = "discovery"
        state.faction_score += 1
        state.quest_progress += 1
        state.main_event_title = "坑道の横穴に関する手がかり"
        state.main_event_state = "ACTIVE"
        if main_quest:
            main_quest.progress += 1
        if not side_quest_001:
            side_quest_001 = Quest(
                world_id=world.world_id,
                quest_id="side_001",
                category="side",
                title="坑道の横穴を調べる",
                status="ACTIVE",
                description="宿で見つけた地図の切れ端を手がかりに、坑道の横穴の存在を確かめる。",
                progress=0,
            )
            db.add(side_quest_001)
        edge = apply_relation_observation(
            db,
            world_id=world.world_id,
            target_key="npc_002",
            display_name=str(RELATION_TARGET_DEFAULTS.get("npc_002", {}).get("display_name", "npc_002")),
            reason="investigation:inn_clue",
            trust_delta=0.02,
            respect_delta=0.03,
        )
        sync_relation_story_quest(db, edge=edge)
    else:
        summary = "周囲を調べたが、目立った発見はなかった。"
        result_type = "none"

    apply_tendency_delta(
        db,
        world_id=world.world_id,
        reason="investigation:inspect",
        deltas={"curious": 1, "cautious": 1},
    )
    apply_world_quest_completion_rules(
        db,
        world_id=world.world_id,
        state=state,
        main_quest=main_quest,
        side_quest_001=side_quest_001,
    )
    sync_security_side_quest(db, world_id=world.world_id, state=state)
    db.add(
        Log(
            world_id=world.world_id,
            log_type="investigation",
            title="調査: 手がかり",
            body=summary,
        )
    )
    db.add(state)
    if main_quest:
        db.add(main_quest)
    if side_quest_001:
        db.add(side_quest_001)
    db.flush()
    return summary, result_type
