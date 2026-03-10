from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.log import Log
from app.models.quest import Quest
from app.models.world_relation_edge import WorldRelationEdge
from app.services.relation_graph_service import build_relation_edge_summary

RELATION_STORY_SEED_CONFIG = {
    "slow_bond": {
        "suffix": "縁の深まり",
        "description": "{name}との関係はまだ静かだが、今後の選択次第で信頼・密命・対立のどれにも育ちうる。",
    },
    "confide_mission": {
        "suffix": "密命",
        "description": "{name}は主人公にだけ重い判断や密かな任務を預けようとしている。",
    },
    "jealous_tension": {
        "suffix": "嫉妬の火種",
        "description": "{name}を巡る感情の軋みが強まり、関係の均衡が揺れ始めている。",
    },
    "worthy_rival": {
        "suffix": "好敵手",
        "description": "{name}は主人公を競争相手として強く意識し、再戦や共闘の物語が生まれつつある。",
    },
    "fragile_dependency": {
        "suffix": "危うい依存",
        "description": "{name}との関係は支えにも鎖にもなりうる不安定さを抱えている。",
    },
    "faith_route": {
        "suffix": "信仰の兆し",
        "description": "{name}は主人公を神託や信仰に連なる存在として見始めている。",
    },
    "resentment_route": {
        "suffix": "遺恨",
        "description": "{name}との関係には決裂や裏切りへ伸びる火種が残っている。",
    },
}


def _build_relation_story_quest_id(target_key: str, seed_key: str) -> str:
    return f"relation_{target_key}_{seed_key}"


def _get_relation_story_quest(db: Session, *, world_id: int, quest_id: str) -> Quest | None:
    return (
        db.query(Quest)
        .filter(Quest.world_id == world_id, Quest.quest_id == quest_id)
        .order_by(Quest.quest_row_id.asc())
        .first()
    )


def _build_relation_story_label(display_name: str, seed_key: str) -> str:
    config = RELATION_STORY_SEED_CONFIG.get(seed_key, {})
    suffix = str(config.get("suffix", seed_key))
    return f"{display_name}との{suffix}"


def sync_relation_story_quest(
    db: Session,
    *,
    edge: WorldRelationEdge,
) -> Quest | None:
    summary = build_relation_edge_summary(
        db,
        world_id=edge.world_id,
        actor_key=edge.actor_key,
        target_key=edge.target_key,
        display_name=edge.display_name,
    )
    story_seeds = list(summary.get("story_seeds", []) or [])
    if not story_seeds:
        return None

    primary_seed = str(story_seeds[0]["seed_key"])
    story_heat = float(summary.get("story_heat", 0.0))
    if primary_seed == "slow_bond" and story_heat < 0.24:
        return None
    if primary_seed != "slow_bond" and story_heat < 0.18:
        return None

    quest_id = _build_relation_story_quest_id(edge.target_key, primary_seed)
    quest = _get_relation_story_quest(db, world_id=edge.world_id, quest_id=quest_id)
    config = RELATION_STORY_SEED_CONFIG.get(primary_seed, {})
    title = _build_relation_story_label(edge.display_name, primary_seed)
    description = str(config.get("description", "{name}との関係が新しい物語へ向かっている。")).format(
        name=edge.display_name
    )

    if not quest:
        quest = Quest(
            world_id=edge.world_id,
            quest_id=quest_id,
            category="relation",
            title=title,
            status="ACTIVE",
            description=description,
            progress=min(2, max(0, int(round(story_heat * 10)) - 1)),
        )
        db.add(quest)
        db.add(
            Log(
                world_id=edge.world_id,
                log_type="relation",
                title=f"関係の火種: {title}",
                body=description,
            )
        )
    elif quest.status != "CLEARED":
        quest.title = title
        quest.description = description
        quest.progress = max(
            int(quest.progress),
            min(3, max(0, int(round(story_heat * 10)) - 1)),
        )
        db.add(quest)

    if quest.progress >= 3 and quest.status != "CLEARED":
        quest.status = "CLEARED"
        db.add(quest)
        db.add(
            Log(
                world_id=edge.world_id,
                log_type="relation",
                title=f"関係進展: {title}",
                body=f"{edge.display_name}との関係は一つの節目に達し、新たな局面へ進んだ。",
            )
        )

    db.flush()
    return quest


def list_relation_story_quests(db: Session, *, world_id: int, limit: int = 5) -> list[dict[str, object]]:
    quests = (
        db.query(Quest)
        .filter(Quest.world_id == world_id, Quest.category == "relation")
        .order_by(Quest.quest_row_id.asc())
        .limit(limit)
        .all()
    )
    items: list[dict[str, object]] = []
    for quest in quests:
        source_target_key = ""
        quest_id = str(quest.quest_id)
        if quest_id.startswith("relation_"):
            remainder = quest_id[len("relation_"):]
            if "_npc_" in f"_{remainder}":
                pass
            parts = remainder.split("_")
            if len(parts) >= 3 and parts[0] == "npc":
                source_target_key = "_".join(parts[:2])
        items.append(
            {
                "quest_id": quest.quest_id,
                "title": quest.title,
                "status": quest.status,
                "progress": quest.progress,
                "summary": quest.description,
                "source_target_key": source_target_key,
            }
        )
    return items
