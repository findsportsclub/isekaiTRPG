from __future__ import annotations

import json
import random
from typing import Any

from sqlalchemy.orm import Session

from app.models.battle_action_declaration import BattleActionDeclaration
from app.models.battle_combatant import BattleCombatant
from app.models.battle_instance import BattleInstance
from app.models.battlefield import Battlefield
from app.services.battle_action_log_service import create_battle_action_log
from app.services.battle_declaration_service import create_battle_action_declaration
from app.services.battle_registry import (
    EffectDefinition,
    RegisteredActionDefinition,
    SpellDefinition,
    get_skill,
    get_spell,
    get_loadout_equipment_keys,
    get_loadout_skill_keys,
    get_loadout_spell_keys,
    build_equipment_bonus_summary,
)
from app.services.enemy_ai_service import AiDecision


def _safe_load_json_object(json_text: str) -> dict[str, Any]:
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


def _safe_load_tags(tags_json: str) -> list[str]:
    return [str(x) for x in _safe_load_json_list(tags_json)]


def _read_snapshot(combatant: BattleCombatant, key: str, default=None):
    snapshot = _safe_load_json_object(combatant.snapshot_json)
    return snapshot.get(key, default)


def _write_snapshot(combatant: BattleCombatant, key: str, value: Any) -> None:
    snapshot = _safe_load_json_object(combatant.snapshot_json)
    snapshot[key] = value
    combatant.snapshot_json = json.dumps(snapshot, ensure_ascii=False)


STATUS_DEFAULT_POTENCY = {
    "poison": 3,
    "burn": 4,
}

STATUS_DEFAULT_AMOUNT = {
    "atk_up": 2,
    "def_up": 2,
}

TURN_START_DECAY_STATUS_KEYS = {"poison", "burn", "atk_up", "def_up"}


def _normalize_status_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    status_key = str(raw.get("status_key", "")).strip().lower()
    if not status_key:
        return None

    try:
        duration = int(raw.get("duration", 0))
    except (TypeError, ValueError):
        duration = 0

    try:
        amount = int(raw.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0

    try:
        potency = int(raw.get("potency", 0))
    except (TypeError, ValueError):
        potency = 0

    return {
        "status_key": status_key,
        "duration": max(0, duration),
        "amount": amount,
        "potency": potency,
    }


def get_combatant_statuses(combatant: BattleCombatant) -> list[dict[str, Any]]:
    raw_statuses = _read_snapshot(combatant, "statuses", [])
    if not isinstance(raw_statuses, list):
        return []

    normalized: list[dict[str, Any]] = []
    for raw in raw_statuses:
        status = _normalize_status_entry(raw)
        if status is not None and status["duration"] > 0:
            normalized.append(status)
    return normalized


def _write_combatant_statuses(combatant: BattleCombatant, statuses: list[dict[str, Any]]) -> None:
    normalized = []
    for raw in statuses:
        status = _normalize_status_entry(raw)
        if status is not None and status["duration"] > 0:
            normalized.append(status)
    _write_snapshot(combatant, "statuses", normalized)


def has_status(combatant: BattleCombatant, status_key: str) -> bool:
    normalized_key = str(status_key).strip().lower()
    return any(
        status["status_key"] == normalized_key
        for status in get_combatant_statuses(combatant)
    )


def apply_status_to_combatant(
    combatant: BattleCombatant,
    *,
    status_key: str,
    duration: int,
    amount: int = 0,
    potency: int = 0,
) -> str | None:
    normalized_key = str(status_key).strip().lower()
    normalized_duration = max(0, int(duration))
    if not normalized_key or normalized_duration <= 0:
        return None

    statuses = get_combatant_statuses(combatant)
    updated = False

    for status in statuses:
        if status["status_key"] != normalized_key:
            continue
        status["duration"] = max(status["duration"], normalized_duration)
        if amount:
            status["amount"] = amount
        if potency:
            status["potency"] = potency
        updated = True
        break

    if not updated:
        statuses.append(
            {
                "status_key": normalized_key,
                "duration": normalized_duration,
                "amount": amount,
                "potency": potency,
            }
        )

    _write_combatant_statuses(combatant, statuses)
    return normalized_key


def consume_stun_turn(combatant: BattleCombatant) -> bool:
    statuses = get_combatant_statuses(combatant)
    consumed = False
    updated: list[dict[str, Any]] = []

    for status in statuses:
        if status["status_key"] == "stun" and not consumed:
            remaining = max(0, status["duration"] - 1)
            consumed = True
            if remaining > 0:
                status["duration"] = remaining
                updated.append(status)
            continue
        updated.append(status)

    if consumed:
        _write_combatant_statuses(combatant, updated)
    return consumed


def resolve_turn_start_statuses_for_combatant(
    combatant: BattleCombatant,
) -> list[dict[str, Any]]:
    statuses = get_combatant_statuses(combatant)
    if not statuses:
        return []

    events: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    can_take_dot_damage = combatant.state == "ACTIVE"

    for status in statuses:
        status_key = status["status_key"]
        remaining_duration = status["duration"]

        if can_take_dot_damage and status_key in {"poison", "burn"}:
            damage_value = max(
                1,
                status["potency"] or STATUS_DEFAULT_POTENCY.get(status_key, 1),
            )
            combatant.hp_current = max(0, combatant.hp_current - damage_value)
            events.append(
                {
                    "status_key": status_key,
                    "damage_value": damage_value,
                    "hp_after": combatant.hp_current,
                    "narrative_result": (
                        f"{combatant.display_name}は毒で{damage_value}ダメージを受けた。"
                        if status_key == "poison"
                        else f"{combatant.display_name}は火傷で{damage_value}ダメージを受けた。"
                    ),
                }
            )

        if status_key in TURN_START_DECAY_STATUS_KEYS:
            remaining_duration = max(0, remaining_duration - 1)
        elif status_key == "stun" and combatant.state != "ACTIVE":
            remaining_duration = max(0, remaining_duration - 1)

        if remaining_duration > 0:
            status["duration"] = remaining_duration
            updated.append(status)

    if combatant.hp_current <= 0:
        combatant.state = "DOWN"

    _write_combatant_statuses(combatant, updated)
    return events


def has_acted_this_turn(combatant: BattleCombatant) -> bool:
    return bool(_read_snapshot(combatant, "acted_this_turn", False))


def mark_acted_this_turn(combatant: BattleCombatant) -> None:
    _write_snapshot(combatant, "acted_this_turn", True)


def clear_acted_this_turn(combatant: BattleCombatant) -> None:
    _write_snapshot(combatant, "acted_this_turn", False)


def _read_loadout_key(combatant: BattleCombatant) -> str:
    return str(_read_snapshot(combatant, "loadout_key", "") or "")


def _read_controller_type(combatant: BattleCombatant) -> str:
    return str(_read_snapshot(combatant, "controller_type", "PLAYER") or "PLAYER")


def _filter_tags_by_battlefield(
    used_tags: list[str],
    battlefield: Battlefield | None,
) -> list[str]:
    if battlefield is None:
        return used_tags

    environment = _safe_load_json_object(battlefield.environment_json)
    terrain = _safe_load_json_object(battlefield.terrain_json)

    valid_tags: list[str] = []

    time_of_day = str(environment.get("time_of_day", "")).lower()
    brightness = str(environment.get("brightness", "")).lower()
    elevation = str(terrain.get("elevation", "")).lower()
    cover = str(terrain.get("cover", "")).lower()
    footing = str(terrain.get("footing", "")).lower()

    for tag in used_tags:
        if tag == "backlight":
            if (
                time_of_day in ["day", "sunset", "morning"]
                and brightness in ["bright", "strong", "high"]
            ):
                valid_tags.append(tag)
        elif tag == "high_ground":
            if elevation in ["high", "medium", "multi_level", "uneven"]:
                valid_tags.append(tag)
        elif tag == "mud_defense":
            if footing in ["muddy", "soft", "swamp", "wet", "unstable"]:
                valid_tags.append(tag)
        elif tag == "cover_use":
            if cover in ["present", "many", "high", "medium"]:
                valid_tags.append(tag)
        else:
            valid_tags.append(tag)

    return valid_tags


def _build_effective_stats(combatant: BattleCombatant) -> dict[str, int]:
    equipment_keys = get_loadout_equipment_keys(_read_loadout_key(combatant))
    eq_bonus = build_equipment_bonus_summary(equipment_keys)
    statuses = get_combatant_statuses(combatant)

    atk_status_bonus = sum(
        status["amount"] or STATUS_DEFAULT_AMOUNT["atk_up"]
        for status in statuses
        if status["status_key"] == "atk_up"
    )
    defense_status_bonus = sum(
        status["amount"] or STATUS_DEFAULT_AMOUNT["def_up"]
        for status in statuses
        if status["status_key"] == "def_up"
    )

    return {
        "atk": combatant.atk + eq_bonus["atk_bonus"] + atk_status_bonus,
        "defense": combatant.defense + eq_bonus["defense_bonus"] + defense_status_bonus,
        "mag": combatant.mag + eq_bonus["mag_bonus"],
        "res": combatant.res + eq_bonus["res_bonus"],
        "spd": combatant.spd + eq_bonus["spd_bonus"],
        "hit": combatant.hit + eq_bonus["hit_bonus"],
        "eva": combatant.eva + eq_bonus["eva_bonus"],
        "crit": combatant.crit + eq_bonus["crit_bonus"],
    }


def _apply_attack_tag_modifiers(
    used_tags: list[str],
    *,
    hit_rate: int,
    crit_rate: int,
) -> tuple[int, int]:
    modified_hit_rate = hit_rate
    modified_crit_rate = crit_rate

    for tag in used_tags:
        if tag == "backlight":
            modified_hit_rate += 6
            modified_crit_rate += 4
        elif tag == "high_ground":
            modified_hit_rate += 8
        elif tag == "feint_attack":
            modified_hit_rate -= 4
            modified_crit_rate += 10

    modified_hit_rate = max(10, min(95, modified_hit_rate))
    modified_crit_rate = max(0, min(50, modified_crit_rate))
    return modified_hit_rate, modified_crit_rate


def _evaluate_battle_state(db: Session, battle_id: int) -> str:
    battle = db.query(BattleInstance).filter(BattleInstance.battle_id == battle_id).first()
    if not battle:
        raise ValueError("battle not found")

    allies_alive = (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side == "ALLY",
            BattleCombatant.state == "ACTIVE",
        )
        .count()
    )
    enemies_alive = (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side == "ENEMY",
            BattleCombatant.state == "ACTIVE",
        )
        .count()
    )

    if enemies_alive == 0:
        battle.state = "RESOLVED"
    elif allies_alive == 0:
        battle.state = "DEFEATED"
    else:
        battle.state = "ACTIVE"

    db.add(battle)
    db.commit()
    db.refresh(battle)
    if battle.state in {"RESOLVED", "DEFEATED"}:
        from app.services.battle_flow_service import finalize_battle_outcome_if_needed

        finalize_battle_outcome_if_needed(db, battle_id)
    return battle.state


def _get_battle_and_battlefield(db: Session, battle_id: int) -> tuple[BattleInstance, Battlefield | None]:
    battle = db.query(BattleInstance).filter(BattleInstance.battle_id == battle_id).first()
    if not battle:
        raise ValueError("battle not found")

    battlefield = None
    if battle.battlefield_id is not None:
        battlefield = (
            db.query(Battlefield)
            .filter(Battlefield.battlefield_id == battle.battlefield_id)
            .first()
        )

    return battle, battlefield


def _get_actor_and_validate(
    db: Session,
    *,
    battle_id: int,
    actor_combatant_id: int,
) -> BattleCombatant:
    actor = (
        db.query(BattleCombatant)
        .filter(BattleCombatant.combatant_id == actor_combatant_id)
        .first()
    )
    if not actor:
        raise ValueError("actor combatant not found")
    if actor.battle_id != battle_id:
        raise ValueError("actor does not belong to the specified battle")
    if actor.state != "ACTIVE":
        raise ValueError("actor is not active")
    if has_acted_this_turn(actor):
        raise ValueError("actor has already acted this turn")
    if has_status(actor, "stun"):
        consume_stun_turn(actor)
        mark_acted_this_turn(actor)
        db.add(actor)
        db.commit()
        raise ValueError("actor is stunned")
    return actor


def _get_target_and_validate(
    db: Session,
    *,
    battle_id: int,
    target_combatant_id: int,
) -> BattleCombatant:
    target = (
        db.query(BattleCombatant)
        .filter(BattleCombatant.combatant_id == target_combatant_id)
        .first()
    )
    if not target:
        raise ValueError("target combatant not found")
    if target.battle_id != battle_id:
        raise ValueError("target does not belong to the specified battle")
    if target.state != "ACTIVE":
        raise ValueError("target is not active")
    return target


def _get_current_cooldown(combatant: BattleCombatant, action_key: str) -> int:
    cooldowns = _read_snapshot(combatant, "cooldowns", {})
    if not isinstance(cooldowns, dict):
        return 0
    return int(cooldowns.get(action_key, 0) or 0)


def _set_current_cooldown(combatant: BattleCombatant, action_key: str, cooldown_value: int) -> None:
    cooldowns = _read_snapshot(combatant, "cooldowns", {})
    if not isinstance(cooldowns, dict):
        cooldowns = {}
    cooldowns[action_key] = max(0, int(cooldown_value))
    _write_snapshot(combatant, "cooldowns", cooldowns)


def reduce_cooldowns_for_combatant(combatant: BattleCombatant) -> None:
    cooldowns = _read_snapshot(combatant, "cooldowns", {})
    if not isinstance(cooldowns, dict):
        cooldowns = {}
    updated = {}
    for key, value in cooldowns.items():
        updated[key] = max(0, int(value) - 1)
    _write_snapshot(combatant, "cooldowns", updated)


def _assert_can_pay_cost(actor: BattleCombatant, resource_type: str, resource_cost: int) -> None:
    if resource_cost <= 0:
        return
    if resource_type == "MP" and actor.mp_current < resource_cost:
        raise ValueError("not enough MP")


def _pay_cost(actor: BattleCombatant, resource_type: str, resource_cost: int) -> None:
    if resource_cost <= 0:
        return
    if resource_type == "MP":
        actor.mp_current = max(0, actor.mp_current - resource_cost)


def get_usable_skills_and_spells(
    actor: BattleCombatant,
) -> dict[str, list[dict[str, Any]]]:
    loadout_key = _read_loadout_key(actor)
    skill_keys = get_loadout_skill_keys(loadout_key)
    spell_keys = get_loadout_spell_keys(loadout_key)

    skill_items: list[dict[str, Any]] = []
    spell_items: list[dict[str, Any]] = []
    actor_is_stunned = has_status(actor, "stun")

    for skill_key in skill_keys:
        skill = get_skill(skill_key)
        if not skill:
            continue
        current_cd = _get_current_cooldown(actor, skill_key)
        usable = True
        reason = ""
        if current_cd > 0:
            usable = False
            reason = "cooldown"
        if skill.resource_type == "MP" and actor.mp_current < skill.resource_cost:
            usable = False
            reason = "not enough MP"
        if actor_is_stunned:
            usable = False
            reason = "stunned"
        skill_items.append(
            {
                "skill_key": skill.skill_key,
                "name": skill.name,
                "category": skill.category,
                "target_type": skill.target_type,
                "resource_type": skill.resource_type,
                "resource_cost": skill.resource_cost,
                "cooldown_turns": skill.cooldown_turns,
                "current_cooldown": current_cd,
                "usable": usable,
                "reason": reason,
            }
        )

    for spell_key in spell_keys:
        spell = get_spell(spell_key)
        if not spell:
            continue
        current_cd = _get_current_cooldown(actor, spell_key)
        usable = True
        reason = ""
        if current_cd > 0:
            usable = False
            reason = "cooldown"
        if spell.resource_type == "MP" and actor.mp_current < spell.resource_cost:
            usable = False
            reason = "not enough MP"
        if actor_is_stunned:
            usable = False
            reason = "stunned"
        spell_items.append(
            {
                "spell_key": spell.spell_key,
                "name": spell.name,
                "category": spell.category,
                "target_type": spell.target_type,
                "resource_type": spell.resource_type,
                "resource_cost": spell.resource_cost,
                "cooldown_turns": spell.cooldown_turns,
                "current_cooldown": current_cd,
                "usable": usable,
                "reason": reason,
            }
        )

    return {
        "skill_items": skill_items,
        "spell_items": spell_items,
    }


def _build_attack_narrative(
    actor_name: str,
    target_name: str,
    declared_tactic_text: str,
    hit_success: bool,
    crit_success: bool,
    damage_value: int,
    defend_triggered: bool,
) -> str:
    if crit_success:
        text = f"{actor_name}の一撃は急所を捉え、{target_name}に{damage_value}ダメージを与えた。"
        if declared_tactic_text:
            text = f"{actor_name}は「{declared_tactic_text}」を狙い、急所を捉える痛烈な一撃を叩き込んだ。"
        if defend_triggered:
            text += " それでも防御によって被害は抑えられた。"
        return text

    if hit_success:
        text = f"{actor_name}の攻撃が命中し、{target_name}に{damage_value}ダメージを与えた。"
        if declared_tactic_text:
            text = f"{actor_name}は「{declared_tactic_text}」を実行し、{target_name}に{damage_value}ダメージを与えた。"
        if defend_triggered:
            text += " 防御によって被害は軽減された。"
        return text

    if declared_tactic_text:
        return f"{actor_name}は「{declared_tactic_text}」を試みたが、{target_name}には届かなかった。"
    return f"{actor_name}の攻撃は{target_name}にかわされた。"


def _build_defend_narrative(
    actor_name: str,
    declared_tactic_text: str,
) -> str:
    if declared_tactic_text:
        return f'{actor_name}は「{declared_tactic_text}」で防御態勢を整えた。'
    return f"{actor_name}は防御態勢を取った。"


def _build_heal_narrative(
    actor_name: str,
    target_name: str,
    heal_value: int,
    spell_name: str,
) -> str:
    return f"{actor_name}は{spell_name}を唱え、{target_name}の傷を癒やした。回復量は{heal_value}。"


SUPPORTED_REGISTERED_EFFECT_TYPES = {
    "direct_damage",
    "heal",
    "guard_up",
    "apply_status",
    "atk_up",
    "def_up",
}


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_registered_definition_key(definition: RegisteredActionDefinition) -> str:
    if isinstance(definition, SpellDefinition):
        return definition.spell_key
    return definition.skill_key


def _resolve_registered_action_type(definition: RegisteredActionDefinition) -> str:
    if isinstance(definition, SpellDefinition):
        return "SPELL"

    effect_types = {effect.effect_type for effect in definition.effect_list}
    if effect_types and effect_types.issubset({"guard_up"}):
        return "DEFEND"
    return "ATTACK"


def _can_resolve_registered_effect_list(definition: RegisteredActionDefinition) -> bool:
    if not definition.effect_list:
        return False
    return all(
        effect.effect_type in SUPPORTED_REGISTERED_EFFECT_TYPES
        for effect in definition.effect_list
    )


def _resolve_registered_target(
    db: Session,
    *,
    battle_id: int,
    actor: BattleCombatant,
    target_combatant_id: int | None,
    target_type: str,
) -> BattleCombatant | None:
    if target_type == "self":
        return actor
    if target_combatant_id is None:
        return None
    return _get_target_and_validate(
        db,
        battle_id=battle_id,
        target_combatant_id=target_combatant_id,
    )


def _default_damage_base(power_formula: str) -> int:
    if power_formula == "basic_magic_power":
        return 10
    return 0


def _default_damage_scale(power_formula: str) -> float:
    if power_formula == "light_physical_power":
        return 0.8
    return 1.0


def _default_damage_variance(power_formula: str) -> int:
    if power_formula in {"basic_physical_power", "basic_magic_power", "light_physical_power"}:
        return 2
    return 0


def _default_crit_multiplier(power_formula: str) -> float:
    if power_formula == "basic_magic_power":
        return 1.4
    return 1.5


def _build_registered_damage_rates(
    *,
    hit_formula: str,
    damage_type: str,
    actor_stats: dict[str, int],
    target_stats: dict[str, int],
    used_tags: list[str],
) -> tuple[int | None, int]:
    if hit_formula == "auto":
        return None, 0

    if hit_formula == "basic_magic_hit":
        hit_rate = max(15, min(95, 78 + actor_stats["hit"] - target_stats["eva"]))
        crit_rate = max(0, min(50, 3 + actor_stats["crit"]))
        return hit_rate, crit_rate

    if hit_formula == "basic_physical_hit" or damage_type != "magic":
        return _apply_attack_tag_modifiers(
            used_tags,
            hit_rate=75 + actor_stats["hit"] - target_stats["eva"],
            crit_rate=5 + actor_stats["crit"],
        )

    hit_rate = max(15, min(95, 78 + actor_stats["hit"] - target_stats["eva"]))
    crit_rate = max(0, min(50, 3 + actor_stats["crit"]))
    return hit_rate, crit_rate


def _consume_defend_snapshot(target: BattleCombatant, damage_value: int) -> tuple[int, bool]:
    defend_active = bool(_read_snapshot(target, "defend_active", False))
    defend_multiplier = _as_float(_read_snapshot(target, "defend_damage_multiplier", 1.0), 1.0)

    if not defend_active:
        return damage_value, False

    reduced_damage = max(1, int(damage_value * defend_multiplier))
    _write_snapshot(target, "defend_active", False)
    _write_snapshot(target, "defend_damage_multiplier", 1.0)
    _write_snapshot(target, "defend_used_tags", [])
    return reduced_damage, True


def _build_registered_damage_narrative(
    *,
    definition: RegisteredActionDefinition,
    actor: BattleCombatant,
    target: BattleCombatant,
    declared_tactic_text: str,
    hit_success: bool,
    crit_success: bool,
    damage_value: int,
    defend_triggered: bool,
) -> str:
    if isinstance(definition, SpellDefinition):
        if hit_success:
            text = f"{actor.display_name}の{definition.name}が{target.display_name}に命中し、{damage_value}ダメージを与えた。"
            if crit_success:
                text = f"{actor.display_name}の{definition.name}が鋭く炸裂し、{target.display_name}に{damage_value}ダメージを与えた。"
            if defend_triggered:
                text += " 防御により被害は軽減された。"
            return text
        return f"{actor.display_name}の{definition.name}は{target.display_name}を捉えきれなかった。"

    return _build_attack_narrative(
        actor_name=actor.display_name,
        target_name=target.display_name,
        declared_tactic_text=declared_tactic_text,
        hit_success=hit_success,
        crit_success=crit_success,
        damage_value=damage_value,
        defend_triggered=defend_triggered,
    )


def _resolve_registered_direct_damage_effect(
    *,
    definition: RegisteredActionDefinition,
    effect: EffectDefinition,
    actor: BattleCombatant,
    target: BattleCombatant,
    actor_stats: dict[str, int],
    target_stats: dict[str, int],
    used_tags: list[str],
    declared_tactic_text: str,
) -> dict[str, Any]:
    payload = effect.effect_payload
    power_formula = str(definition.power_formula or "").strip()
    hit_formula = str(definition.hit_formula or "").strip()
    damage_type = str(payload.get("damage_type", "physical")).strip().lower() or "physical"

    hit_rate, crit_rate = _build_registered_damage_rates(
        hit_formula=hit_formula,
        damage_type=damage_type,
        actor_stats=actor_stats,
        target_stats=target_stats,
        used_tags=used_tags,
    )

    hit_success = True if hit_rate is None else (random.randint(1, 100) <= hit_rate)
    crit_success = hit_success and crit_rate > 0 and (random.randint(1, 100) <= crit_rate)

    damage_value = 0
    defend_triggered = False

    if hit_success:
        attack_stat_key = "mag" if damage_type == "magic" else "atk"
        defense_stat_key = "res" if damage_type == "magic" else "defense"
        base_damage = max(
            1,
            actor_stats[attack_stat_key]
            - target_stats[defense_stat_key]
            + _as_int(payload.get("base"), _default_damage_base(power_formula)),
        )
        scaled_damage = max(
            1,
            int(
                round(
                    base_damage
                    * _as_float(payload.get("power_scale"), _default_damage_scale(power_formula))
                )
            ),
        )
        variance = max(0, _as_int(payload.get("variance"), _default_damage_variance(power_formula)))
        damage_value = max(1, scaled_damage + random.randint(-variance, variance))

        if crit_success:
            damage_value = max(
                1,
                int(
                    damage_value
                    * _as_float(
                        payload.get("crit_multiplier"),
                        _default_crit_multiplier(power_formula),
                    )
                ),
            )

        damage_value, defend_triggered = _consume_defend_snapshot(target, damage_value)
        target.hp_current = max(0, target.hp_current - damage_value)
        if target.hp_current <= 0:
            target.state = "DOWN"

    narrative_result = _build_registered_damage_narrative(
        definition=definition,
        actor=actor,
        target=target,
        declared_tactic_text=declared_tactic_text,
        hit_success=hit_success,
        crit_success=crit_success,
        damage_value=damage_value,
        defend_triggered=defend_triggered,
    )

    return {
        "result_type": "CRITICAL" if crit_success else ("HIT" if hit_success else "MISS"),
        "hit_success": hit_success,
        "crit_success": crit_success,
        "guard_success": defend_triggered,
        "evade_success": not hit_success,
        "damage_value": damage_value,
        "hp_after": target.hp_current,
        "target_combatant_id": target.combatant_id,
        "applied_statuses": [],
        "narrative_result": narrative_result,
    }


def _resolve_registered_heal_effect(
    *,
    definition: RegisteredActionDefinition,
    effect: EffectDefinition,
    actor: BattleCombatant,
    target: BattleCombatant,
    actor_stats: dict[str, int],
) -> dict[str, Any]:
    payload = effect.effect_payload
    scale_stat = str(payload.get("scale_stat", "mag")).strip().lower() or "mag"
    variance_min = _as_int(payload.get("variance_min"), 0)
    variance_max = _as_int(payload.get("variance_max"), variance_min)
    if variance_max < variance_min:
        variance_max = variance_min

    heal_value = max(
        1,
        _as_int(payload.get("base"), 0)
        + actor_stats.get(scale_stat, 0)
        + random.randint(variance_min, variance_max),
    )
    target.hp_current = min(target.hp_max, target.hp_current + heal_value)

    return {
        "result_type": "HEAL",
        "hit_success": True,
        "crit_success": False,
        "guard_success": False,
        "evade_success": False,
        "damage_value": -heal_value,
        "hp_after": target.hp_current,
        "target_combatant_id": target.combatant_id,
        "applied_statuses": [],
        "narrative_result": _build_heal_narrative(
            actor_name=actor.display_name,
            target_name=target.display_name,
            heal_value=heal_value,
            spell_name=definition.name,
        ),
    }


def _resolve_registered_guard_up_effect(
    *,
    actor: BattleCombatant,
    effect: EffectDefinition,
    used_tags: list[str],
    declared_tactic_text: str,
) -> dict[str, Any]:
    payload = effect.effect_payload
    defense_multiplier = _as_float(payload.get("multiplier"), 1.0)

    tag_multipliers = payload.get("tag_multipliers", {})
    if isinstance(tag_multipliers, dict):
        for tag_name, tag_multiplier in tag_multipliers.items():
            if str(tag_name) in used_tags:
                defense_multiplier = _as_float(tag_multiplier, defense_multiplier)

    _write_snapshot(actor, "defend_active", True)
    _write_snapshot(actor, "defend_damage_multiplier", defense_multiplier)
    _write_snapshot(actor, "defend_used_tags", used_tags)

    return {
        "result_type": "GUARD",
        "hit_success": False,
        "crit_success": False,
        "guard_success": True,
        "evade_success": False,
        "damage_value": 0,
        "hp_after": actor.hp_current,
        "target_combatant_id": None,
        "applied_statuses": [],
        "narrative_result": _build_defend_narrative(
            actor_name=actor.display_name,
            declared_tactic_text=declared_tactic_text,
        ),
    }


def _resolve_registered_status_effect(
    *,
    actor: BattleCombatant,
    target: BattleCombatant,
    status_key: str,
    duration: int,
    amount: int = 0,
    potency: int = 0,
) -> dict[str, Any]:
    applied_status = apply_status_to_combatant(
        target,
        status_key=status_key,
        duration=duration,
        amount=amount,
        potency=potency,
    )

    target_name = target.display_name
    if status_key == "poison":
        text = f"{actor.display_name}は{target_name}を毒状態にした。"
    elif status_key == "burn":
        text = f"{actor.display_name}は{target_name}を火傷状態にした。"
    elif status_key == "stun":
        text = f"{actor.display_name}は{target_name}を行動不能にした。"
    elif status_key == "atk_up":
        text = f"{target_name}の攻撃力が上がった。"
    else:
        text = f"{target_name}の防御力が上がった。"

    return {
        "result_type": "STATUS",
        "hit_success": True,
        "crit_success": False,
        "guard_success": False,
        "evade_success": False,
        "damage_value": 0,
        "hp_after": target.hp_current,
        "target_combatant_id": target.combatant_id,
        "applied_statuses": [applied_status] if applied_status else [],
        "narrative_result": text,
    }


def _merge_registered_effect_results(effect_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not effect_results:
        raise ValueError("effect result is required")

    result_type = "GUARD"
    if any(result["result_type"] == "CRITICAL" for result in effect_results):
        result_type = "CRITICAL"
    elif any(result["result_type"] == "HIT" for result in effect_results):
        result_type = "HIT"
    elif any(result["result_type"] == "MISS" for result in effect_results):
        result_type = "MISS"
    elif any(result["result_type"] == "HEAL" for result in effect_results):
        result_type = "HEAL"
    elif any(result["result_type"] == "STATUS" for result in effect_results):
        result_type = "STATUS"

    target_combatant_id = None
    hp_after = _as_int(effect_results[-1]["hp_after"], 0)
    for result in reversed(effect_results):
        if result["target_combatant_id"] is not None:
            target_combatant_id = result["target_combatant_id"]
            hp_after = _as_int(result["hp_after"], hp_after)
            break

    return {
        "result_type": result_type,
        "hit_success": any(result["hit_success"] for result in effect_results),
        "crit_success": any(result["crit_success"] for result in effect_results),
        "guard_success": any(result["guard_success"] for result in effect_results),
        "evade_success": any(result["evade_success"] for result in effect_results),
        "damage_value": sum(_as_int(result["damage_value"], 0) for result in effect_results),
        "hp_after": hp_after,
        "target_combatant_id": target_combatant_id,
        "applied_statuses": [
            str(status_key)
            for result in effect_results
            for status_key in result.get("applied_statuses", [])
            if status_key
        ],
        "narrative_result": " ".join(
            str(result["narrative_result"]).strip()
            for result in effect_results
            if str(result["narrative_result"]).strip()
        ),
    }


def _resolve_registered_effect_list(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor: BattleCombatant,
    definition: RegisteredActionDefinition,
    target_combatant_id: int | None,
    resource_type: str,
    resource_cost: int,
    cooldown_turns: int,
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration | None:
    if not _can_resolve_registered_effect_list(definition):
        return None

    _battle, battlefield = _get_battle_and_battlefield(db, battle_id)
    resolved_target = _resolve_registered_target(
        db,
        battle_id=battle_id,
        actor=actor,
        target_combatant_id=target_combatant_id,
        target_type=definition.target_type,
    )

    needs_target = any(
        effect.effect_type in {"direct_damage", "heal"}
        for effect in definition.effect_list
    )
    if needs_target and resolved_target is None:
        raise ValueError("target is required")

    action_type = _resolve_registered_action_type(definition)
    declaration = create_battle_action_declaration(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor.combatant_id,
        action_type=action_type,
        primary_target_combatant_id=None if definition.target_type == "self" else target_combatant_id,
        skill_id=_get_registered_definition_key(definition) if isinstance(definition, SpellDefinition) else "",
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )

    declared_tags = _safe_load_tags(declaration.parsed_tags_json)
    used_tags = _filter_tags_by_battlefield(declared_tags, battlefield)
    actor_stats = _build_effective_stats(actor)

    effect_results: list[dict[str, Any]] = []
    touched_combatants: dict[int, BattleCombatant] = {actor.combatant_id: actor}

    for effect in definition.effect_list:
        if effect.effect_type == "direct_damage":
            if resolved_target is None:
                raise ValueError("target is required")
            effect_results.append(
                _resolve_registered_direct_damage_effect(
                    definition=definition,
                    effect=effect,
                    actor=actor,
                    target=resolved_target,
                    actor_stats=actor_stats,
                    target_stats=_build_effective_stats(resolved_target),
                    used_tags=used_tags,
                    declared_tactic_text=declared_tactic_text,
                )
            )
            touched_combatants[resolved_target.combatant_id] = resolved_target
            continue

        if effect.effect_type == "heal":
            if resolved_target is None:
                raise ValueError("target is required")
            effect_results.append(
                _resolve_registered_heal_effect(
                    definition=definition,
                    effect=effect,
                    actor=actor,
                    target=resolved_target,
                    actor_stats=actor_stats,
                )
            )
            touched_combatants[resolved_target.combatant_id] = resolved_target
            continue

        if effect.effect_type in {"apply_status", "atk_up", "def_up"}:
            status_target = actor if resolved_target is None else resolved_target
            status_key = (
                str(effect.effect_payload.get("status_key", "")).strip().lower()
                if effect.effect_type == "apply_status"
                else effect.effect_type
            )
            if not status_key:
                raise ValueError("status_key is required")

            effect_results.append(
                _resolve_registered_status_effect(
                    actor=actor,
                    target=status_target,
                    status_key=status_key,
                    duration=max(1, _as_int(effect.effect_payload.get("duration"), 1)),
                    amount=_as_int(
                        effect.effect_payload.get("amount"),
                        STATUS_DEFAULT_AMOUNT.get(status_key, 0),
                    ),
                    potency=_as_int(
                        effect.effect_payload.get("potency"),
                        STATUS_DEFAULT_POTENCY.get(status_key, 0),
                    ),
                )
            )
            touched_combatants[status_target.combatant_id] = status_target
            continue

        guard_target = actor if resolved_target is None else resolved_target
        effect_results.append(
            _resolve_registered_guard_up_effect(
                actor=guard_target,
                effect=effect,
                used_tags=used_tags,
                declared_tactic_text=declared_tactic_text,
            )
        )
        touched_combatants[guard_target.combatant_id] = guard_target

    _pay_cost(actor, resource_type, resource_cost)
    _set_current_cooldown(actor, _get_registered_definition_key(definition), cooldown_turns)

    merged_result = _merge_registered_effect_results(effect_results)

    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration.declaration_id,
        actor_combatant_id=actor.combatant_id,
        target_combatant_id=merged_result["target_combatant_id"],
        result_type=merged_result["result_type"],
        hit_success=merged_result["hit_success"],
        crit_success=merged_result["crit_success"],
        guard_success=merged_result["guard_success"],
        evade_success=merged_result["evade_success"],
        damage_value=merged_result["damage_value"],
        hp_after=merged_result["hp_after"],
        applied_statuses=merged_result["applied_statuses"],
        declared_tactic_text=declared_tactic_text,
        used_tags=used_tags,
        narrative_result=merged_result["narrative_result"],
    )

    mark_acted_this_turn(actor)
    declaration.resolution_status = "RESOLVED"

    for combatant in touched_combatants.values():
        db.add(combatant)
    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    _evaluate_battle_state(db, battle_id)
    return declaration


def resolve_basic_attack(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int,
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    _battle, battlefield = _get_battle_and_battlefield(db, battle_id)
    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)
    target = _get_target_and_validate(db, battle_id=battle_id, target_combatant_id=target_combatant_id)

    actor_stats = _build_effective_stats(actor)
    target_stats = _build_effective_stats(target)

    declaration = create_battle_action_declaration(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor_combatant_id,
        action_type="ATTACK",
        primary_target_combatant_id=target_combatant_id,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )

    declared_tags = _safe_load_tags(declaration.parsed_tags_json)
    used_tags = _filter_tags_by_battlefield(declared_tags, battlefield)

    base_hit_rate = 75 + actor_stats["hit"] - target_stats["eva"]
    base_crit_rate = 5 + actor_stats["crit"]

    hit_rate, crit_rate = _apply_attack_tag_modifiers(
        used_tags,
        hit_rate=base_hit_rate,
        crit_rate=base_crit_rate,
    )

    hit_success = random.randint(1, 100) <= hit_rate
    crit_success = hit_success and (random.randint(1, 100) <= crit_rate)

    damage_value = 0
    defend_triggered = False

    if hit_success:
        base_damage = max(1, actor_stats["atk"] - target_stats["defense"])
        damage_value = max(1, base_damage + random.randint(-2, 2))
        if crit_success:
            damage_value = int(damage_value * 1.5)

        defend_active = bool(_read_snapshot(target, "defend_active", False))
        defend_multiplier = float(_read_snapshot(target, "defend_damage_multiplier", 1.0))

        if defend_active:
            damage_value = max(1, int(damage_value * defend_multiplier))
            _write_snapshot(target, "defend_active", False)
            _write_snapshot(target, "defend_damage_multiplier", 1.0)
            _write_snapshot(target, "defend_used_tags", [])
            defend_triggered = True

        target.hp_current = max(0, target.hp_current - damage_value)
        if target.hp_current <= 0:
            target.state = "DOWN"

    narrative_result = _build_attack_narrative(
        actor_name=actor.display_name,
        target_name=target.display_name,
        declared_tactic_text=declared_tactic_text,
        hit_success=hit_success,
        crit_success=crit_success,
        damage_value=damage_value,
        defend_triggered=defend_triggered,
    )

    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration.declaration_id,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=target_combatant_id,
        result_type="CRITICAL" if crit_success else ("HIT" if hit_success else "MISS"),
        hit_success=hit_success,
        crit_success=crit_success,
        guard_success=defend_triggered,
        evade_success=not hit_success,
        damage_value=damage_value,
        hp_after=target.hp_current,
        applied_statuses=[],
        declared_tactic_text=declared_tactic_text,
        used_tags=used_tags,
        narrative_result=narrative_result,
    )

    mark_acted_this_turn(actor)
    declaration.resolution_status = "RESOLVED"

    db.add(actor)
    db.add(target)
    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    _evaluate_battle_state(db, battle_id)
    return declaration


def resolve_basic_defend(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    _battle, battlefield = _get_battle_and_battlefield(db, battle_id)
    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)

    declaration = create_battle_action_declaration(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor_combatant_id,
        action_type="DEFEND",
        primary_target_combatant_id=None,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )

    declared_tags = _safe_load_tags(declaration.parsed_tags_json)
    used_tags = _filter_tags_by_battlefield(declared_tags, battlefield)

    defense_multiplier = 1.0
    if "mud_defense" in used_tags:
        defense_multiplier = 0.9

    _write_snapshot(actor, "defend_active", True)
    _write_snapshot(actor, "defend_damage_multiplier", defense_multiplier)
    _write_snapshot(actor, "defend_used_tags", used_tags)

    narrative_result = _build_defend_narrative(
        actor_name=actor.display_name,
        declared_tactic_text=declared_tactic_text,
    )

    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration.declaration_id,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=None,
        result_type="GUARD",
        hit_success=False,
        crit_success=False,
        guard_success=True,
        evade_success=False,
        damage_value=0,
        hp_after=actor.hp_current,
        applied_statuses=[],
        declared_tactic_text=declared_tactic_text,
        used_tags=used_tags,
        narrative_result=narrative_result,
    )

    mark_acted_this_turn(actor)
    declaration.resolution_status = "RESOLVED"

    db.add(actor)
    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    _evaluate_battle_state(db, battle_id)
    return declaration


def resolve_minor_heal_spell(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int,
    spell_key: str = "minor_heal",
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    spell = get_spell(spell_key)
    if not spell:
        raise ValueError("spell not found")

    _battle, _battlefield = _get_battle_and_battlefield(db, battle_id)
    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)
    target = _get_target_and_validate(db, battle_id=battle_id, target_combatant_id=target_combatant_id)

    current_cd = _get_current_cooldown(actor, spell_key)
    if current_cd > 0:
        raise ValueError("spell is on cooldown")
    _assert_can_pay_cost(actor, spell.resource_type, spell.resource_cost)

    actor_stats = _build_effective_stats(actor)

    declaration = create_battle_action_declaration(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor_combatant_id,
        action_type="SPELL",
        primary_target_combatant_id=target_combatant_id,
        skill_id=spell_key,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )

    heal_value = max(1, 8 + actor_stats["mag"] + random.randint(0, 3))
    target.hp_current = min(target.hp_max, target.hp_current + heal_value)

    _pay_cost(actor, spell.resource_type, spell.resource_cost)
    _set_current_cooldown(actor, spell_key, spell.cooldown_turns)

    narrative_result = _build_heal_narrative(
        actor_name=actor.display_name,
        target_name=target.display_name,
        heal_value=heal_value,
        spell_name=spell.name,
    )

    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration.declaration_id,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=target_combatant_id,
        result_type="HEAL",
        hit_success=True,
        crit_success=False,
        guard_success=False,
        evade_success=False,
        damage_value=-heal_value,
        hp_after=target.hp_current,
        applied_statuses=[],
        declared_tactic_text=declared_tactic_text,
        used_tags=[],
        narrative_result=narrative_result,
    )

    mark_acted_this_turn(actor)
    declaration.resolution_status = "RESOLVED"

    db.add(actor)
    db.add(target)
    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    _evaluate_battle_state(db, battle_id)
    return declaration


def resolve_ember_shot_spell(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int,
    spell_key: str = "ember_shot",
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    spell = get_spell(spell_key)
    if not spell:
        raise ValueError("spell not found")

    _battle, _battlefield = _get_battle_and_battlefield(db, battle_id)
    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)
    target = _get_target_and_validate(db, battle_id=battle_id, target_combatant_id=target_combatant_id)

    current_cd = _get_current_cooldown(actor, spell_key)
    if current_cd > 0:
        raise ValueError("spell is on cooldown")
    _assert_can_pay_cost(actor, spell.resource_type, spell.resource_cost)

    actor_stats = _build_effective_stats(actor)
    target_stats = _build_effective_stats(target)

    declaration = create_battle_action_declaration(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor_combatant_id,
        action_type="SPELL",
        primary_target_combatant_id=target_combatant_id,
        skill_id=spell_key,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )

    hit_rate = max(15, min(95, 78 + actor_stats["hit"] - target_stats["eva"]))
    hit_success = random.randint(1, 100) <= hit_rate
    crit_success = hit_success and (random.randint(1, 100) <= max(0, min(50, 3 + actor_stats["crit"])))

    damage_value = 0
    defend_triggered = False

    if hit_success:
        base_damage = max(1, 10 + actor_stats["mag"] - target_stats["res"])
        damage_value = max(1, base_damage + random.randint(-2, 2))
        if crit_success:
            damage_value = int(damage_value * 1.4)

        defend_active = bool(_read_snapshot(target, "defend_active", False))
        defend_multiplier = float(_read_snapshot(target, "defend_damage_multiplier", 1.0))

        if defend_active:
            damage_value = max(1, int(damage_value * defend_multiplier))
            _write_snapshot(target, "defend_active", False)
            _write_snapshot(target, "defend_damage_multiplier", 1.0)
            _write_snapshot(target, "defend_used_tags", [])
            defend_triggered = True

        target.hp_current = max(0, target.hp_current - damage_value)
        if target.hp_current <= 0:
            target.state = "DOWN"

    _pay_cost(actor, spell.resource_type, spell.resource_cost)
    _set_current_cooldown(actor, spell_key, spell.cooldown_turns)

    narrative_result = (
        f"{actor.display_name}の{spell.name}が{target.display_name}に命中し、{damage_value}ダメージを与えた。"
        if hit_success
        else f"{actor.display_name}の{spell.name}は{target.display_name}を捉えきれなかった。"
    )
    if defend_triggered and hit_success:
        narrative_result += " 防御により被害は軽減された。"

    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration.declaration_id,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=target_combatant_id,
        result_type="CRITICAL" if crit_success else ("HIT" if hit_success else "MISS"),
        hit_success=hit_success,
        crit_success=crit_success,
        guard_success=defend_triggered,
        evade_success=not hit_success,
        damage_value=damage_value,
        hp_after=target.hp_current,
        applied_statuses=[],
        declared_tactic_text=declared_tactic_text,
        used_tags=[],
        narrative_result=narrative_result,
    )

    mark_acted_this_turn(actor)
    declaration.resolution_status = "RESOLVED"

    db.add(actor)
    db.add(target)
    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    _evaluate_battle_state(db, battle_id)
    return declaration


def resolve_registered_skill(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int | None,
    skill_key: str,
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    skill = get_skill(skill_key)
    if not skill:
        raise ValueError("skill not found")

    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)
    available = get_loadout_skill_keys(_read_loadout_key(actor))
    if skill_key not in available:
        raise ValueError("skill is not available for actor")

    current_cd = _get_current_cooldown(actor, skill_key)
    if current_cd > 0:
        raise ValueError("skill is on cooldown")
    _assert_can_pay_cost(actor, skill.resource_type, skill.resource_cost)

    declaration = _resolve_registered_effect_list(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor=actor,
        definition=skill,
        target_combatant_id=target_combatant_id,
        resource_type=skill.resource_type,
        resource_cost=skill.resource_cost,
        cooldown_turns=skill.cooldown_turns,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )
    if declaration is not None:
        return declaration

    if skill_key == "basic_strike":
        if target_combatant_id is None:
            raise ValueError("target is required")
        declaration = resolve_basic_attack(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            target_combatant_id=target_combatant_id,
            declared_tactic_text=declared_tactic_text,
            risk_level=risk_level,
        )
        _pay_cost(actor, skill.resource_type, skill.resource_cost)
        _set_current_cooldown(actor, skill_key, skill.cooldown_turns)
        db.add(actor)
        db.commit()
        return declaration

    if skill_key == "guard_stance":
        declaration = resolve_basic_defend(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            declared_tactic_text=declared_tactic_text,
            risk_level=risk_level,
        )
        _pay_cost(actor, skill.resource_type, skill.resource_cost)
        _set_current_cooldown(actor, skill_key, skill.cooldown_turns)
        db.add(actor)
        db.commit()
        return declaration

    if skill_key == "quick_feint":
        if target_combatant_id is None:
            raise ValueError("target is required")
        return resolve_basic_attack(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            target_combatant_id=target_combatant_id,
            declared_tactic_text=declared_tactic_text or "一度引くふりをしてから突き込む",
            risk_level=risk_level,
        )

    raise ValueError("skill is not yet implemented")


def resolve_registered_spell(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int | None,
    spell_key: str,
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    spell = get_spell(spell_key)
    if not spell:
        raise ValueError("spell not found")

    actor = _get_actor_and_validate(db, battle_id=battle_id, actor_combatant_id=actor_combatant_id)
    available = get_loadout_spell_keys(_read_loadout_key(actor))
    if spell_key not in available:
        raise ValueError("spell is not available for actor")

    current_cd = _get_current_cooldown(actor, spell_key)
    if current_cd > 0:
        raise ValueError("spell is on cooldown")
    _assert_can_pay_cost(actor, spell.resource_type, spell.resource_cost)

    declaration = _resolve_registered_effect_list(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        actor=actor,
        definition=spell,
        target_combatant_id=target_combatant_id,
        resource_type=spell.resource_type,
        resource_cost=spell.resource_cost,
        cooldown_turns=spell.cooldown_turns,
        declared_tactic_text=declared_tactic_text,
        risk_level=risk_level,
    )
    if declaration is not None:
        return declaration

    if target_combatant_id is None:
        raise ValueError("target is required")

    if spell_key == "minor_heal":
        return resolve_minor_heal_spell(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            target_combatant_id=target_combatant_id,
            spell_key=spell_key,
            declared_tactic_text=declared_tactic_text,
            risk_level=risk_level,
        )

    if spell_key == "ember_shot":
        return resolve_ember_shot_spell(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            target_combatant_id=target_combatant_id,
            spell_key=spell_key,
            declared_tactic_text=declared_tactic_text,
            risk_level=risk_level,
        )

    raise ValueError("spell is not yet implemented")


def resolve_ai_decision(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    decision: AiDecision,
) -> BattleActionDeclaration | None:
    action_type = decision.selected_action_type.upper().strip()

    if action_type == "ATTACK":
        if decision.selected_target_id is None:
            return None
        return resolve_basic_attack(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            target_combatant_id=decision.selected_target_id,
            declared_tactic_text=decision.selected_tactic_text,
            risk_level="LOW",
        )

    if action_type == "DEFEND":
        return resolve_basic_defend(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            actor_combatant_id=actor_combatant_id,
            declared_tactic_text=decision.selected_tactic_text,
            risk_level="LOW",
        )

    if action_type == "SPELL":
        actor = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == actor_combatant_id)
            .first()
        )
        if not actor or decision.selected_target_id is None:
            return None

        target = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == decision.selected_target_id)
            .first()
        )
        if not target:
            return None

        available_spell_keys = get_loadout_spell_keys(_read_loadout_key(actor))
        if actor.side == target.side and "minor_heal" in available_spell_keys:
            return resolve_registered_spell(
                db,
                battle_id=battle_id,
                turn_no=turn_no,
                actor_combatant_id=actor_combatant_id,
                target_combatant_id=decision.selected_target_id,
                spell_key="minor_heal",
                declared_tactic_text=decision.selected_tactic_text,
                risk_level="LOW",
            )
        if "ember_shot" in available_spell_keys:
            return resolve_registered_spell(
                db,
                battle_id=battle_id,
                turn_no=turn_no,
                actor_combatant_id=actor_combatant_id,
                target_combatant_id=decision.selected_target_id,
                spell_key="ember_shot",
                declared_tactic_text=decision.selected_tactic_text,
                risk_level="LOW",
            )

    return None
