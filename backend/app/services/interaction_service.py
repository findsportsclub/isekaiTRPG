from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.quest import Quest
from app.models.world import World
from app.models.world_state import WorldState
from app.services.campaign_phase_service import get_or_create_campaign_state, read_narrative_state
from app.services.relationship_service import (
    apply_relationship_delta,
    get_relationship_snapshot,
)
from app.services.relation_graph_service import (
    RELATION_TARGET_DEFAULTS,
    apply_relation_interaction,
    build_relation_edge_summary,
)
from app.services.relation_story_service import sync_relation_story_quest
from app.services.tendency_service import (
    apply_tendency_delta,
    get_or_create_tendency_state,
    get_primary_tendency,
    read_tendency_scores,
)
from app.services.world_progress_service import apply_world_quest_completion_rules

INTERACTION_TARGETS_BY_LOCATION: dict[str, list[dict[str, str]]] = {
    "はじまりの村": [
        {"target_key": "npc_001", "display_name": "村長", "summary": "北坑道の不穏さを気にかけている。"},
        {"target_key": "npc_002", "display_name": "宿屋の主人", "summary": "旅人たちの噂をよく拾っている。"},
    ],
    "村の入口": [
        {"target_key": "npc_003", "display_name": "見張りの青年", "summary": "街道で見た異変を覚えている。"},
    ],
    "北坑道前": [
        {"target_key": "npc_004", "display_name": "鉱夫の老人", "summary": "坑道の奥から響く音を恐れている。"},
    ],
    "宿屋": [
        {"target_key": "npc_002", "display_name": "宿屋の主人", "summary": "旅人たちから新しい噂を聞いている。"},
        {"target_key": "npc_005", "display_name": "旅人", "summary": "坑道に関する怪しい地図を持っていたらしい。"},
    ],
}


def list_interaction_targets(world: World) -> list[dict[str, str]]:
    return [item.copy() for item in INTERACTION_TARGETS_BY_LOCATION.get(world.current_location, [])]


ATTITUDE_LABELS = {
    "honest": "率直に話す",
    "kind": "柔らかく話す",
    "calm": "落ち着いて話す",
    "cold": "距離を取って話す",
    "threatening": "圧をかけて話す",
}

INTENT_LABELS = {
    "help": "助力を申し出る",
    "information": "情報を引き出す",
    "probe": "反応を探る",
    "pressure": "揺さぶりをかける",
}


def _choose_recommended_attitude(
    *,
    reaction_label: str,
    primary_tendency: str,
    tone: str,
) -> tuple[str, str]:
    if reaction_label == "guarded":
        return "calm", "相手が警戒しているため、圧を抑えて距離を詰める方が通りやすい。"
    if reaction_label in {"warm", "trusted"}:
        return "honest", "すでに関係が温まっているため、率直さが最も信頼に繋がりやすい。"
    if tone == "desperate":
        return "calm", "場が張りつめているため、まず落ち着いた態度で話を通す方が崩れにくい。"
    if primary_tendency in {"pragmatic", "bold"}:
        return "calm", "押しの強さが出やすい傾向なので、少し抑えた態度が安定する。"
    if primary_tendency in {"curious", "cautious"}:
        return "honest", "慎重さが強い今は、余計な駆け引きより率直さの方が情報を引き出しやすい。"
    return "kind", "現段階では敵対を生みにくい柔らかな態度が最も無難。"


def _choose_recommended_intent(
    *,
    reaction_label: str,
    primary_tendency: str,
    weight: str,
) -> tuple[str, str]:
    if reaction_label in {"warm", "trusted"}:
        return "information", "関係ができている相手からは、素直に情報を求めるのが最も実利的。"
    if reaction_label == "guarded":
        return "help", "警戒中の相手には、まず利害の一致を見せる方が関係悪化を避けやすい。"
    if weight in {"major", "climax"}:
        return "information", "場面の重みが高いため、曖昧さより明確な情報収集を優先したい。"
    if primary_tendency == "curious":
        return "probe", "探索志向が強まっているので、相手の反応を探る選択が自然。"
    return "help", "まず協力姿勢を見せる方が、関係と情報の両方を取りやすい。"


def build_interaction_choice_suggestions(
    db: Session,
    *,
    world: World,
    target_key: str | None,
) -> dict[str, object]:
    campaign_state = get_or_create_campaign_state(db, world.world_id)
    narrative_state = read_narrative_state(campaign_state)
    tendency_state = get_or_create_tendency_state(db, world_id=world.world_id)
    scores = read_tendency_scores(tendency_state)
    primary_tendency = get_primary_tendency(scores)

    reaction_label = "neutral"
    if target_key:
        reaction = get_relationship_snapshot(
            db,
            world_id=world.world_id,
            target_key=target_key,
        )
        reaction_label = str(reaction["reaction_label"])

    recommended_attitude, attitude_reason = _choose_recommended_attitude(
        reaction_label=reaction_label,
        primary_tendency=primary_tendency,
        tone=str(narrative_state.get("tone", "calm")),
    )
    recommended_intent, intent_reason = _choose_recommended_intent(
        reaction_label=reaction_label,
        primary_tendency=primary_tendency,
        weight=str(narrative_state.get("weight", "normal")),
    )

    attitude_options = []
    for value, label in ATTITUDE_LABELS.items():
        reason = "現在の空気と相手反応に最も噛み合う。" if value == recommended_attitude else "選べる態度の一つ。"
        if value == recommended_attitude:
            reason = attitude_reason
        attitude_options.append(
            {
                "value": value,
                "label": label,
                "recommended": value == recommended_attitude,
                "reason": reason,
            }
        )

    intent_options = []
    for value, label in INTENT_LABELS.items():
        reason = "現在の場面に対して無難な狙い。" if value != recommended_intent else intent_reason
        intent_options.append(
            {
                "value": value,
                "label": label,
                "recommended": value == recommended_intent,
                "reason": reason,
            }
        )

    return {
        "recommended_attitude_tone": recommended_attitude,
        "recommended_intent_tag": recommended_intent,
        "attitude_tone_options": attitude_options,
        "intent_tag_options": intent_options,
    }


def execute_interaction(
    db: Session,
    *,
    world: World,
    state: WorldState,
    main_quest: Quest | None,
    side_quest_001: Quest | None,
    target_key: str,
    attitude_tone: str | None,
    intent_tag: str | None,
) -> tuple[str, str]:
    result_type = "none"
    summary = "その相手とはうまく話せなかった。"

    if target_key == "npc_001":
        summary = "村長は、北坑道の霧が日ごとに濃くなっていると語った。"
        result_type = "info"
        state.faction_score += 1
        state.quest_progress += 1
        if main_quest:
            main_quest.progress += 1
    elif target_key == "npc_002":
        summary = "宿屋の主人は、坑道へ向かった旅人が戻っていないと教えてくれた。"
        result_type = "rumor"
        state.demon_score += 1
        state.quest_progress += 1
        if main_quest:
            main_quest.progress += 1
    elif target_key == "npc_003":
        summary = "見張りの青年は、夜明け前に街道を横切る影を見たと話した。"
        result_type = "info"
        state.faction_score += 1
        state.quest_progress += 1
        if main_quest:
            main_quest.progress += 1
    elif target_key == "npc_004":
        summary = "鉱夫の老人は、坑道の奥から金属を擦るような音が聞こえたと言った。"
        result_type = "warning"
        state.dungeon_score += 1
        state.quest_progress += 1
        if main_quest:
            main_quest.progress += 1
    elif target_key == "npc_005":
        summary = "旅人は、宿で聞いた噂として『坑道には地図にない横穴がある』と囁いた。"
        result_type = "rumor"
        state.dungeon_score += 1
        state.quest_progress += 1
        if main_quest:
            main_quest.progress += 1

    trust_delta = 0.05
    affinity_delta = 0.04
    normalized_tone = str(attitude_tone or "").lower()
    normalized_intent = str(intent_tag or "").lower()
    if normalized_tone in {"cold", "threatening", "hostile"}:
        trust_delta -= 0.06
        affinity_delta -= 0.05
    elif normalized_tone in {"kind", "gentle", "honest"}:
        trust_delta += 0.04
        affinity_delta += 0.03
    if normalized_intent in {"probe", "pressure"}:
        affinity_delta -= 0.03

    apply_relationship_delta(
        db,
        world_id=world.world_id,
        target_key=target_key,
        interaction_type="talk",
        trust_delta=trust_delta,
        affinity_delta=affinity_delta,
    )
    edge = apply_relation_interaction(
        db,
        world_id=world.world_id,
        actor_key="hero",
        target_key=target_key,
        display_name=str(RELATION_TARGET_DEFAULTS.get(target_key, {}).get("display_name", target_key)),
        interaction_type="interaction:talk",
        attitude_tone=attitude_tone,
        intent_tag=intent_tag,
    )
    sync_relation_story_quest(db, edge=edge)

    tendency_delta = {"honest": 1, "protective": 1}
    if normalized_tone in {"cold", "threatening", "hostile"}:
        tendency_delta = {"pragmatic": 1, "bold": 1}
    elif normalized_intent in {"probe", "information"}:
        tendency_delta = {"curious": 1, "cautious": 1}
    apply_tendency_delta(
        db,
        world_id=world.world_id,
        reason="interaction:talk",
        deltas=tendency_delta,
    )

    apply_world_quest_completion_rules(
        db,
        world_id=world.world_id,
        state=state,
        main_quest=main_quest,
        side_quest_001=side_quest_001,
    )

    db.add(
        Log(
            world_id=world.world_id,
            log_type="interaction",
            title="交流: 会話",
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


def build_interaction_relation_summary(
    db: Session,
    *,
    world: World,
    target_key: str | None,
) -> dict[str, object] | None:
    if not target_key:
        return None
    return build_relation_edge_summary(
        db,
        world_id=world.world_id,
        actor_key="hero",
        target_key=target_key,
        display_name=str(RELATION_TARGET_DEFAULTS.get(target_key, {}).get("display_name", target_key)),
    )
