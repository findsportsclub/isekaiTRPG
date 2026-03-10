from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.battle_combatant import BattleCombatant
from app.models.battle_instance import BattleInstance
from app.models.battlefield import Battlefield


def _safe_load_json_dict(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _safe_load_json_list(json_text: str) -> list[Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _read_snapshot(combatant: BattleCombatant, key: str, default=None):
    snapshot = _safe_load_json_dict(combatant.snapshot_json)
    return snapshot.get(key, default)


def _hp_ratio(combatant: BattleCombatant) -> float:
    if combatant.hp_max <= 0:
        return 0.0
    return combatant.hp_current / combatant.hp_max


def _get_active_allies_and_enemies(
    db: Session,
    *,
    battle_id: int,
    actor: BattleCombatant,
) -> tuple[list[BattleCombatant], list[BattleCombatant]]:
    allies = (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side == actor.side,
            BattleCombatant.state == "ACTIVE",
        )
        .order_by(BattleCombatant.combatant_id.asc())
        .all()
    )
    enemies = (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side != actor.side,
            BattleCombatant.state == "ACTIVE",
        )
        .order_by(BattleCombatant.combatant_id.asc())
        .all()
    )
    return allies, enemies


def _get_battlefield_summary(db: Session, battle: BattleInstance) -> dict[str, Any]:
    if battle.battlefield_id is None:
        return {
            "name": "",
            "terrain": {},
            "environment": {},
            "movement_rules": {},
            "tactical_bias": {},
        }

    battlefield = (
        db.query(Battlefield)
        .filter(Battlefield.battlefield_id == battle.battlefield_id)
        .first()
    )
    if not battlefield:
        return {
            "name": "",
            "terrain": {},
            "environment": {},
            "movement_rules": {},
            "tactical_bias": {},
        }

    return {
        "name": battlefield.name,
        "terrain": _safe_load_json_dict(battlefield.terrain_json),
        "environment": _safe_load_json_dict(battlefield.environment_json),
        "movement_rules": _safe_load_json_dict(battlefield.movement_rules_json),
        "tactical_bias": _safe_load_json_dict(battlefield.tactical_bias_json),
    }


def _build_legal_actions(actor: BattleCombatant) -> list[str]:
    legal_actions = ["ATTACK", "DEFEND"]

    spell_keys = _safe_load_json_list(json.dumps(_read_snapshot(actor, "available_spell_keys", []), ensure_ascii=False))
    if spell_keys:
        legal_actions.append("SPELL")

    return legal_actions


def _summarize_combatant(c: BattleCombatant) -> dict[str, Any]:
    return {
        "combatant_id": c.combatant_id,
        "display_name": c.display_name,
        "side": c.side,
        "role": c.role,
        "hp_current": c.hp_current,
        "hp_max": c.hp_max,
        "hp_ratio": round(_hp_ratio(c), 3),
        "mp_current": c.mp_current,
        "mp_max": c.mp_max,
        "state": c.state,
        "atk": c.atk,
        "defense": c.defense,
        "mag": c.mag,
        "res": c.res,
        "spd": c.spd,
    }


def build_named_ai_context(
    db: Session,
    *,
    battle: BattleInstance,
    actor: BattleCombatant,
    profile: Any,
    order_understood: bool,
    order_obeyed: bool,
    communication_blocked: bool,
) -> dict[str, Any]:
    allies, enemies = _get_active_allies_and_enemies(db, battle_id=battle.battle_id, actor=actor)

    return {
        "battle": {
            "battle_id": battle.battle_id,
            "turn_no": battle.turn_no,
            "state": battle.state,
            "objective_type": battle.objective_type,
            "location_id": battle.location_id,
        },
        "battlefield": _get_battlefield_summary(db, battle),
        "actor": _summarize_combatant(actor),
        "actor_profile": {
            "profile_key": getattr(profile, "profile_key", ""),
            "controller_type": getattr(profile, "controller_type", ""),
            "combat_role": getattr(profile, "combat_role", ""),
            "behavior_mode": getattr(profile, "behavior_mode", ""),
            "base_traits": getattr(profile, "base_traits", {}),
            "dynamic_traits": getattr(profile, "dynamic_traits", {}),
            "growth_stats": getattr(profile, "growth_stats", {}),
            "relationship_modifiers": getattr(profile, "relationship_modifiers", {}),
            "temporary_state_tags": getattr(profile, "temporary_state_tags", []),
            "combat_experience": getattr(profile, "combat_experience", "LOW"),
            "tactical_judgment": getattr(profile, "tactical_judgment", "LOW"),
            "morale": getattr(profile, "morale", 0.5),
            "panic_action_rate": getattr(profile, "panic_action_rate", 0.0),
            "hesitation_rate": getattr(profile, "hesitation_rate", 0.0),
            "misplay_tendency": getattr(profile, "misplay_tendency", 0.0),
            "command_obedience": getattr(profile, "command_obedience", 0.5),
            "command_comprehension": getattr(profile, "command_comprehension", 0.5),
            "teamwork_skill": getattr(profile, "teamwork_skill", 0.5),
        },
        "allies": [_summarize_combatant(c) for c in allies],
        "enemies": [_summarize_combatant(c) for c in enemies],
        "legal_actions": _build_legal_actions(actor),
        "available_skill_keys": _read_snapshot(actor, "available_skill_keys", []),
        "available_spell_keys": _read_snapshot(actor, "available_spell_keys", []),
        "equipped_item_keys": _read_snapshot(actor, "equipped_item_keys", []),
        "order": {
            "text": getattr(profile, "current_order_text", ""),
            "priority": getattr(profile, "current_order_priority", "NORMAL"),
            "understood": order_understood,
            "obeyed": order_obeyed,
            "communication_blocked": communication_blocked,
        },
    }


def maybe_call_external_named_ai(context: dict[str, Any]) -> dict[str, Any] | None:
    """
    将来ここを OpenAI API 等へ接続する。
    現段階では未接続なので None を返す。
    返す場合の想定フォーマット:
    {
        "selected_action_type": "ATTACK" | "DEFEND" | "SPELL" | "WAIT",
        "selected_target_id": 12 | None,
        "selected_tactic_text": "...",
        "reason_summary": "..."
    }
    """
    return None


def _pick_low_hp_target(summary_list: list[dict[str, Any]]) -> int | None:
    if not summary_list:
        return None
    sorted_list = sorted(summary_list, key=lambda x: (x.get("hp_ratio", 1.0), x.get("combatant_id", 999999)))
    return int(sorted_list[0]["combatant_id"])


def _pick_ally_need_heal(summary_list: list[dict[str, Any]]) -> int | None:
    low = [x for x in summary_list if float(x.get("hp_ratio", 1.0)) <= 0.5]
    if not low:
        return None
    low = sorted(low, key=lambda x: (x.get("hp_ratio", 1.0), x.get("combatant_id", 999999)))
    return int(low[0]["combatant_id"])


def _fallback_named_ai_decision(context: dict[str, Any]) -> dict[str, Any]:
    actor = context["actor"]
    profile = context["actor_profile"]
    legal_actions = context["legal_actions"]
    allies = context["allies"]
    enemies = context["enemies"]
    order = context["order"]
    available_spell_keys = context["available_spell_keys"]

    hp_ratio = float(actor.get("hp_ratio", 1.0))
    morale = float(profile.get("morale", 0.5))
    behavior_mode = str(profile.get("behavior_mode", "calculated"))
    combat_role = str(profile.get("combat_role", ""))

    # 命令が理解され、従う場合
    if order.get("obeyed") and isinstance(order.get("text"), str) and order["text"]:
        order_text = str(order["text"])

        if any(word in order_text for word in ["守", "防御", "耐え", "下がれ"]):
            if "DEFEND" in legal_actions:
                return {
                    "selected_action_type": "DEFEND",
                    "selected_target_id": None,
                    "selected_tactic_text": "命令に従い、無駄な消耗を避けるよう構える",
                    "reason_summary": "命令を優先し、防御行動を選択した。",
                }

        if any(word in order_text for word in ["回復", "治", "支援"]) and "SPELL" in legal_actions:
            heal_target = _pick_ally_need_heal(allies)
            if heal_target is not None and "minor_heal" in available_spell_keys:
                return {
                    "selected_action_type": "SPELL",
                    "selected_target_id": heal_target,
                    "selected_tactic_text": "命令に従い、負傷者の回復を優先する",
                    "reason_summary": "命令を優先し、回復行動を選択した。",
                }

        if any(word in order_text for word in ["術師", "後衛", "弱い敵", "瀕死"]) and enemies:
            target_id = _pick_low_hp_target(enemies)
            return {
                "selected_action_type": "ATTACK",
                "selected_target_id": target_id,
                "selected_tactic_text": "命令意図を汲み、崩しやすい標的を優先する",
                "reason_summary": "命令を優先し、狙う対象を選択した。",
            }

    # ヒーラー寄り
    if combat_role in {"healer", "support"} and "SPELL" in legal_actions and "minor_heal" in available_spell_keys:
        heal_target = _pick_ally_need_heal(allies)
        if heal_target is not None:
            return {
                "selected_action_type": "SPELL",
                "selected_target_id": heal_target,
                "selected_tactic_text": "乱れた陣形を立て直すため、傷ついた味方を癒やす",
                "reason_summary": "役割に従い、負傷者の回復を優先した。",
            }

    # 低HPなら慎重化
    if hp_ratio <= 0.35 and (morale < 0.65 or behavior_mode in {"calculated", "supportive", "protective"}):
        if "DEFEND" in legal_actions:
            return {
                "selected_action_type": "DEFEND",
                "selected_target_id": None,
                "selected_tactic_text": "ここで崩れれば主導権を失う。まずは体勢を立て直す",
                "reason_summary": "損耗と士気を考慮し、防御を優先した。",
            }

    # 魔法攻撃が得意なら火弾
    if "SPELL" in legal_actions and "ember_shot" in available_spell_keys and actor.get("mag", 0) >= actor.get("atk", 0):
        target_id = _pick_low_hp_target(enemies)
        return {
            "selected_action_type": "SPELL",
            "selected_target_id": target_id,
            "selected_tactic_text": "敵の乱れた箇所へ火弾を通す",
            "reason_summary": "能力傾向に基づき、魔法攻撃を選択した。",
        }

    # 既定: 攻撃
    target_id = _pick_low_hp_target(enemies)
    return {
        "selected_action_type": "ATTACK",
        "selected_target_id": target_id,
        "selected_tactic_text": "戦況の綻びを見極め、最も崩しやすい敵へ圧を掛ける",
        "reason_summary": "ネームドAIの標準判断として攻撃を選択した。",
    }


def _normalize_named_ai_candidate(
    candidate: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    legal_actions = set(context["legal_actions"])
    allies = {int(x["combatant_id"]) for x in context["allies"]}
    enemies = {int(x["combatant_id"]) for x in context["enemies"]}
    actor_side = str(context["actor"]["side"])

    action = str(candidate.get("selected_action_type", "ATTACK")).upper().strip()
    target_id = candidate.get("selected_target_id")
    tactic = str(candidate.get("selected_tactic_text", "")).strip()
    reason = str(candidate.get("reason_summary", "")).strip()

    if action not in legal_actions:
        action = "ATTACK" if "ATTACK" in legal_actions else "DEFEND"

    if action == "ATTACK":
        if not isinstance(target_id, int) or target_id not in enemies:
            target_id = next(iter(enemies), None)

    elif action == "SPELL":
        # SPELL は味方回復 or 敵攻撃のどちらもありうる
        if not isinstance(target_id, int):
            if actor_side == "ALLY":
                # まず味方低HP優先、その後敵
                if allies:
                    target_id = next(iter(allies), None)
                if target_id is None and enemies:
                    target_id = next(iter(enemies), None)
            else:
                target_id = next(iter(enemies), None)

    elif action in {"DEFEND", "WAIT"}:
        target_id = None

    if not tactic:
        tactic = "状況に応じて行動する"
    if not reason:
        reason = "妥当な合法行動へ正規化した。"

    return {
        "selected_action_type": action,
        "selected_target_id": target_id,
        "selected_tactic_text": tactic,
        "reason_summary": reason,
    }


def decide_named_or_unique_action(
    db: Session,
    *,
    battle: BattleInstance,
    actor: BattleCombatant,
    profile: Any,
    order_understood: bool,
    order_obeyed: bool,
    communication_blocked: bool,
) -> dict[str, Any]:
    context = build_named_ai_context(
        db,
        battle=battle,
        actor=actor,
        profile=profile,
        order_understood=order_understood,
        order_obeyed=order_obeyed,
        communication_blocked=communication_blocked,
    )

    external_candidate = maybe_call_external_named_ai(context)
    candidate = external_candidate or _fallback_named_ai_decision(context)

    normalized = _normalize_named_ai_candidate(
        candidate,
        context=context,
    )

    return normalized