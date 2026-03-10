from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.world_relation_edge import WorldRelationEdge

DEFAULT_BOND_METRICS = {
    "trust": 0.0,
    "affection": 0.0,
    "loyalty": 0.0,
    "fear": 0.0,
    "respect": 0.0,
    "dependency": 0.0,
    "resentment": 0.0,
    "jealousy": 0.0,
    "duty": 0.0,
    "debt": 0.0,
    "faith": 0.0,
    "political_value": 0.0,
    "ideological_alignment": 0.0,
    "intimacy": 0.0,
    "rivalry_heat": 0.0,
}

DEFAULT_SUPPORT_PROFILE = {
    "emotional": 0.0,
    "informational": 0.0,
    "instrumental": 0.0,
    "appraisal": 0.0,
}

RELATION_TARGET_DEFAULTS: dict[str, dict[str, object]] = {
    "npc_001": {
        "display_name": "村長",
        "relation_frame": "hierarchical",
        "relation_type": "mentor",
        "attachment_style": "secure",
        "support_profile": {"informational": 0.5, "appraisal": 0.4},
    },
    "npc_002": {
        "display_name": "宿屋の主人",
        "relation_frame": "reciprocal",
        "relation_type": "ally",
        "attachment_style": "secure",
        "support_profile": {"emotional": 0.2, "informational": 0.5, "instrumental": 0.3},
    },
    "npc_003": {
        "display_name": "見張りの青年",
        "relation_frame": "reciprocal",
        "relation_type": "comrade",
        "attachment_style": "anxious",
        "support_profile": {"informational": 0.4, "instrumental": 0.2},
    },
    "npc_004": {
        "display_name": "鉱夫の老人",
        "relation_frame": "communal",
        "relation_type": "witness",
        "attachment_style": "avoidant",
        "support_profile": {"informational": 0.4},
    },
    "npc_005": {
        "display_name": "旅人",
        "relation_frame": "transactional",
        "relation_type": "stranger",
        "attachment_style": "avoidant",
        "support_profile": {"informational": 0.4},
    },
}


def _safe_load_dict(text: str, *, default: dict[str, float] | None = None) -> dict[str, float]:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {
                str(key): float(value)
                for key, value in data.items()
                if isinstance(key, str) and isinstance(value, (int, float))
            }
    except Exception:
        pass
    return dict(default or {})


def _safe_load_list(text: str) -> list[str]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        pass
    return []


def _safe_dump_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False)


def _resolve_target_defaults(target_key: str, display_name: str | None = None) -> dict[str, object]:
    defaults = dict(RELATION_TARGET_DEFAULTS.get(target_key, {}))
    defaults.setdefault("display_name", display_name or target_key)
    defaults.setdefault("relation_frame", "communal")
    defaults.setdefault("relation_type", "acquaintance")
    defaults.setdefault("attachment_style", "secure")
    defaults.setdefault("support_profile", {})
    return defaults


def get_or_create_relation_edge(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
    target_key: str,
    display_name: str | None = None,
) -> WorldRelationEdge:
    edge = (
        db.query(WorldRelationEdge)
        .filter(
            WorldRelationEdge.world_id == world_id,
            WorldRelationEdge.actor_key == actor_key,
            WorldRelationEdge.target_key == target_key,
        )
        .first()
    )
    if edge:
        return edge

    defaults = _resolve_target_defaults(target_key, display_name)
    edge = WorldRelationEdge(
        world_id=world_id,
        actor_key=actor_key,
        target_key=target_key,
        display_name=str(defaults["display_name"]),
        relation_frame=str(defaults["relation_frame"]),
        relation_type=str(defaults["relation_type"]),
        attachment_style=str(defaults["attachment_style"]),
        support_profile_json=_safe_dump_json(
            {**DEFAULT_SUPPORT_PROFILE, **dict(defaults.get("support_profile", {}) or {})}
        ),
        bond_metrics_json=_safe_dump_json(DEFAULT_BOND_METRICS),
        story_flags_json="[]",
    )
    db.add(edge)
    db.flush()
    return edge


def read_bond_metrics(edge: WorldRelationEdge) -> dict[str, float]:
    merged = {**DEFAULT_BOND_METRICS, **_safe_load_dict(edge.bond_metrics_json, default=DEFAULT_BOND_METRICS)}
    return {key: round(float(value), 3) for key, value in merged.items()}


def _write_bond_metrics(edge: WorldRelationEdge, metrics: dict[str, float]) -> None:
    edge.bond_metrics_json = _safe_dump_json(
        {key: round(float(metrics.get(key, 0.0)), 3) for key in DEFAULT_BOND_METRICS}
    )


def read_story_flags(edge: WorldRelationEdge) -> list[str]:
    return _safe_load_list(edge.story_flags_json)


def _write_story_flags(edge: WorldRelationEdge, flags: list[str]) -> None:
    deduped: list[str] = []
    for flag in flags:
        normalized = str(flag).strip()
        if normalized and normalized not in deduped:
            deduped.append(normalized)
    edge.story_flags_json = _safe_dump_json(deduped)


def _update_relation_type(metrics: dict[str, float], current_type: str) -> str:
    if metrics["affection"] >= 0.55 and metrics["trust"] >= 0.45:
        return "confidant"
    if metrics["loyalty"] >= 0.45 and metrics["respect"] >= 0.45:
        return "sworn_ally"
    if metrics["resentment"] >= 0.45 and metrics["trust"] <= 0.1:
        return "rival"
    if metrics["fear"] >= 0.45 and metrics["trust"] < 0.0:
        return "strained"
    return current_type


def _derive_story_seeds(edge: WorldRelationEdge, metrics: dict[str, float]) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []
    if metrics["trust"] >= 0.4 and metrics["duty"] >= 0.2:
        seeds.append(
            {
                "seed_key": "confide_mission",
                "label": "密命の委任",
                "summary": f"{edge.display_name}は秘密や重い判断を預ける相手として主人公を見始めている。",
            }
        )
    if metrics["affection"] >= 0.45 and metrics["jealousy"] >= 0.2:
        seeds.append(
            {
                "seed_key": "jealous_tension",
                "label": "嫉妬混じりの緊張",
                "summary": f"{edge.display_name}との距離が縮まるほど、別の関係を巡る軋みが生まれやすい。",
            }
        )
    if metrics["respect"] >= 0.4 and metrics["rivalry_heat"] >= 0.25:
        seeds.append(
            {
                "seed_key": "worthy_rival",
                "label": "好敵手化",
                "summary": f"{edge.display_name}は競争や対立の先にある対等さを意識し始めている。",
            }
        )
    if metrics["dependency"] >= 0.35 and metrics["trust"] < 0.25:
        seeds.append(
            {
                "seed_key": "fragile_dependency",
                "label": "危うい依存",
                "summary": f"{edge.display_name}は頼りつつも安心しきれておらず、歪んだ結びつきへ傾く恐れがある。",
            }
        )
    if metrics["faith"] >= 0.35:
        seeds.append(
            {
                "seed_key": "faith_route",
                "label": "信仰的接近",
                "summary": f"{edge.display_name}は主人公を信仰や神託に結びつく存在として見始めている。",
            }
        )
    if metrics["resentment"] >= 0.35:
        seeds.append(
            {
                "seed_key": "resentment_route",
                "label": "遺恨の火種",
                "summary": f"{edge.display_name}との関係には後の決裂や裏切りに繋がる火種がある。",
            }
        )
    if not seeds:
        seeds.append(
            {
                "seed_key": "slow_bond",
                "label": "静かな関係進行",
                "summary": f"{edge.display_name}との関係はまだ小さいが、今後の言葉と共闘で大きく変わりうる。",
            }
        )
    return seeds[:3]


def apply_relation_interaction(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
    target_key: str,
    display_name: str | None,
    interaction_type: str,
    attitude_tone: str | None,
    intent_tag: str | None,
) -> WorldRelationEdge:
    edge = get_or_create_relation_edge(
        db,
        world_id=world_id,
        actor_key=actor_key,
        target_key=target_key,
        display_name=display_name,
    )
    metrics = read_bond_metrics(edge)
    flags = read_story_flags(edge)
    tone = str(attitude_tone or "").lower()
    intent = str(intent_tag or "").lower()

    metrics["trust"] += 0.08
    metrics["affection"] += 0.05
    metrics["respect"] += 0.03
    metrics["duty"] += 0.02
    metrics["intimacy"] += 0.02
    if tone in {"honest", "kind", "calm"}:
        metrics["trust"] += 0.05
        metrics["affection"] += 0.03
    if tone in {"cold", "threatening", "hostile"}:
        metrics["trust"] -= 0.12
        metrics["affection"] -= 0.08
        metrics["fear"] += 0.09
        metrics["resentment"] += 0.07
        metrics["rivalry_heat"] += 0.04
    if intent == "help":
        metrics["loyalty"] += 0.04
        metrics["dependency"] += 0.02
    elif intent == "information":
        metrics["respect"] += 0.03
    elif intent == "probe":
        metrics["trust"] -= 0.02
        metrics["respect"] += 0.02
        metrics["rivalry_heat"] += 0.03
    elif intent == "pressure":
        metrics["fear"] += 0.08
        metrics["resentment"] += 0.08
        metrics["trust"] -= 0.05

    metrics = {key: max(-1.0, min(1.0, round(value, 3))) for key, value in metrics.items()}
    _write_bond_metrics(edge, metrics)

    if metrics["trust"] >= 0.35 and "shared_confidence" not in flags:
        flags.append("shared_confidence")
    if metrics["affection"] >= 0.35 and "emotional_bond" not in flags:
        flags.append("emotional_bond")
    if metrics["resentment"] >= 0.3 and "tension_present" not in flags:
        flags.append("tension_present")

    story_seeds = _derive_story_seeds(edge, metrics)
    edge.story_heat = round(max(0.0, min(1.0, float(edge.story_heat) + 0.12 + max(0.0, metrics["trust"]) * 0.05)), 3)
    edge.relation_type = _update_relation_type(metrics, edge.relation_type)
    edge.interaction_count += 1
    edge.last_story_seed = story_seeds[0]["seed_key"]
    edge.last_updated_reason = interaction_type
    _write_story_flags(edge, flags)
    db.add(edge)
    db.flush()
    return edge


def apply_relation_observation(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
    target_key: str,
    display_name: str | None,
    reason: str,
    trust_delta: float = 0.0,
    respect_delta: float = 0.0,
    loyalty_delta: float = 0.0,
    resentment_delta: float = 0.0,
) -> WorldRelationEdge:
    edge = get_or_create_relation_edge(
        db,
        world_id=world_id,
        actor_key=actor_key,
        target_key=target_key,
        display_name=display_name,
    )
    metrics = read_bond_metrics(edge)
    metrics["trust"] += trust_delta
    metrics["respect"] += respect_delta
    metrics["loyalty"] += loyalty_delta
    metrics["resentment"] += resentment_delta
    metrics = {key: max(-1.0, min(1.0, round(value, 3))) for key, value in metrics.items()}
    _write_bond_metrics(edge, metrics)
    edge.story_heat = round(max(0.0, min(1.0, float(edge.story_heat) + 0.05 + max(0.0, respect_delta))), 3)
    edge.relation_type = _update_relation_type(metrics, edge.relation_type)
    edge.interaction_count += 1
    edge.last_story_seed = _derive_story_seeds(edge, metrics)[0]["seed_key"]
    edge.last_updated_reason = reason
    db.add(edge)
    db.flush()
    return edge


def build_relation_edge_summary(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
    target_key: str,
    display_name: str | None = None,
) -> dict[str, object]:
    edge = get_or_create_relation_edge(
        db,
        world_id=world_id,
        actor_key=actor_key,
        target_key=target_key,
        display_name=display_name,
    )
    metrics = read_bond_metrics(edge)
    return {
        "actor_key": actor_key,
        "target_key": target_key,
        "display_name": edge.display_name,
        "relation_frame": edge.relation_frame,
        "relation_type": edge.relation_type,
        "attachment_style": edge.attachment_style,
        "story_heat": round(float(edge.story_heat), 3),
        "trust": metrics["trust"],
        "affection": metrics["affection"],
        "loyalty": metrics["loyalty"],
        "fear": metrics["fear"],
        "respect": metrics["respect"],
        "dependency": metrics["dependency"],
        "resentment": metrics["resentment"],
        "faith": metrics["faith"],
        "political_value": metrics["political_value"],
        "story_flags": read_story_flags(edge),
        "story_seeds": _derive_story_seeds(edge, metrics),
    }


def list_relation_story_hints(db: Session, *, world_id: int, actor_key: str = "hero", limit: int = 3) -> list[str]:
    edges = (
        db.query(WorldRelationEdge)
        .filter(WorldRelationEdge.world_id == world_id, WorldRelationEdge.actor_key == actor_key)
        .order_by(WorldRelationEdge.story_heat.desc(), WorldRelationEdge.interaction_count.desc())
        .limit(limit)
        .all()
    )
    hints: list[str] = []
    for edge in edges:
        story_seed = _derive_story_seeds(edge, read_bond_metrics(edge))[0]
        hints.append(f"{edge.display_name}:{story_seed['label']}")
    return hints


def list_top_relation_summaries(
    db: Session,
    *,
    world_id: int,
    actor_key: str = "hero",
    limit: int = 3,
) -> list[dict[str, object]]:
    edges = (
        db.query(WorldRelationEdge)
        .filter(WorldRelationEdge.world_id == world_id, WorldRelationEdge.actor_key == actor_key)
        .order_by(WorldRelationEdge.story_heat.desc(), WorldRelationEdge.interaction_count.desc())
        .limit(limit)
        .all()
    )
    return [
        build_relation_edge_summary(
            db,
            world_id=world_id,
            actor_key=actor_key,
            target_key=edge.target_key,
            display_name=edge.display_name,
        )
        for edge in edges
    ]
