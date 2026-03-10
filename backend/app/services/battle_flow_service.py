from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.battle_combatant import BattleCombatant
from app.models.battlefield import Battlefield
from app.models.battlefield_gimmick import BattlefieldGimmick
from app.models.battle_instance import BattleInstance
from app.services.battle_action_log_service import create_battle_action_log
from app.services.enemy_ai_service import (
    decide_action_for_combatant,
    apply_post_battle_progression,
    upsert_world_combatant_progress,
)
from app.services.world_progress_service import apply_battle_resolution_world_progress
from app.services.simple_battle_resolver import (
    has_acted_this_turn,
    clear_acted_this_turn,
    mark_acted_this_turn,
    resolve_ai_decision,
    reduce_cooldowns_for_combatant,
    has_status,
    consume_stun_turn,
    resolve_turn_start_statuses_for_combatant,
)


# =========================
# 基本取得
# =========================

def get_battle(db: Session, battle_id: int) -> BattleInstance:
    battle = db.query(BattleInstance).filter(BattleInstance.battle_id == battle_id).first()
    if not battle:
        raise ValueError("battle not found")
    return battle


def get_combatants_for_battle(db: Session, battle_id: int) -> list[BattleCombatant]:
    return (
        db.query(BattleCombatant)
        .filter(BattleCombatant.battle_id == battle_id)
        .order_by(BattleCombatant.spd.desc(), BattleCombatant.combatant_id.asc())
        .all()
    )


def _safe_load_json_dict(json_text: str) -> dict[str, Any]:
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _write_json_dict(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def get_battlefield_for_battle(db: Session, battle: BattleInstance) -> Battlefield | None:
    if battle.battlefield_id is None:
        return None
    return (
        db.query(Battlefield)
        .filter(Battlefield.battlefield_id == battle.battlefield_id)
        .first()
    )


def get_enabled_gimmicks_for_battle(
    db: Session,
    battle: BattleInstance,
) -> list[BattlefieldGimmick]:
    if battle.battlefield_id is None:
        return []
    return (
        db.query(BattlefieldGimmick)
        .filter(
            BattlefieldGimmick.battlefield_id == battle.battlefield_id,
            BattlefieldGimmick.enabled_flag.is_(True),
        )
        .order_by(BattlefieldGimmick.sort_order.asc(), BattlefieldGimmick.gimmick_id.asc())
        .all()
    )


def _read_battle_gimmick_runtime(battle: BattleInstance) -> dict[str, Any]:
    snapshot = _safe_load_json_dict(battle.battle_difficulty_snapshot_json)
    runtime = snapshot.get("gimmick_runtime", {})
    if isinstance(runtime, dict):
        return runtime
    return {}


def _write_battle_gimmick_runtime(battle: BattleInstance, runtime: dict[str, Any]) -> None:
    snapshot = _safe_load_json_dict(battle.battle_difficulty_snapshot_json)
    snapshot["gimmick_runtime"] = runtime
    battle.battle_difficulty_snapshot_json = _write_json_dict(snapshot)


def _read_battle_finalize_runtime(battle: BattleInstance) -> dict[str, Any]:
    snapshot = _safe_load_json_dict(battle.battle_difficulty_snapshot_json)
    runtime = snapshot.get("finalize_runtime", {})
    if isinstance(runtime, dict):
        return runtime
    return {}


def _write_battle_finalize_runtime(battle: BattleInstance, runtime: dict[str, Any]) -> None:
    snapshot = _safe_load_json_dict(battle.battle_difficulty_snapshot_json)
    snapshot["finalize_runtime"] = runtime
    battle.battle_difficulty_snapshot_json = _write_json_dict(snapshot)


def _is_battle_outcome_finalized(battle: BattleInstance) -> bool:
    runtime = _read_battle_finalize_runtime(battle)
    return bool(runtime.get("completed", False))


def _mark_battle_outcome_finalized(
    battle: BattleInstance,
    *,
    quest_progress_delta: int = 0,
    main_quest_progress_delta: int = 0,
    demon_score_delta: int = 0,
) -> None:
    runtime = _read_battle_finalize_runtime(battle)
    runtime["completed"] = True
    runtime["finalized_state"] = battle.state
    runtime["finalized_turn_no"] = battle.turn_no
    runtime["quest_progress_delta"] = quest_progress_delta
    runtime["main_quest_progress_delta"] = main_quest_progress_delta
    runtime["demon_score_delta"] = demon_score_delta
    _write_battle_finalize_runtime(battle, runtime)


def _has_gimmick_fired_once(battle: BattleInstance, gimmick_id: int) -> bool:
    runtime = _read_battle_gimmick_runtime(battle)
    fired_ids = runtime.get("fired_once_gimmick_ids", [])
    if not isinstance(fired_ids, list):
        return False
    return gimmick_id in [int(x) for x in fired_ids if str(x).isdigit()]


def _mark_gimmick_fired_once(battle: BattleInstance, gimmick_id: int) -> None:
    runtime = _read_battle_gimmick_runtime(battle)
    fired_ids = runtime.get("fired_once_gimmick_ids", [])
    if not isinstance(fired_ids, list):
        fired_ids = []
    normalized = [int(x) for x in fired_ids if str(x).isdigit()]
    if gimmick_id not in normalized:
        normalized.append(gimmick_id)
    runtime["fired_once_gimmick_ids"] = normalized
    _write_battle_gimmick_runtime(battle, runtime)


def _set_battle_visibility_level(battle: BattleInstance, visibility_level: str) -> None:
    runtime = _read_battle_gimmick_runtime(battle)
    runtime["visibility_level"] = visibility_level
    _write_battle_gimmick_runtime(battle, runtime)


def _gimmick_matches_timing(
    battle: BattleInstance,
    gimmick: BattlefieldGimmick,
    *,
    timing: str,
    turn_no: int,
) -> bool:
    trigger_type = str(gimmick.trigger_type or "").upper().strip()
    trigger_detail = gimmick.read_trigger_detail()
    expected_timing = str(trigger_detail.get("timing", trigger_type)).upper().strip()
    timing_key = timing.upper().strip()

    if trigger_type == "TURN_ELAPSED":
        event_timing = expected_timing or "TURN_START"
        if event_timing != timing_key:
            return False
        every_n_turns = max(1, int(trigger_detail.get("every_n_turns", 1) or 1))
        start_turn = max(1, int(trigger_detail.get("start_turn", 1) or 1))
        if turn_no < start_turn:
            return False
        if (turn_no - start_turn) % every_n_turns != 0:
            return False
    elif expected_timing != timing_key:
        return False

    if str(gimmick.repeat_rule or "ONCE").upper().strip() == "ONCE":
        return not _has_gimmick_fired_once(battle, gimmick.gimmick_id)
    return True


def _select_gimmick_targets(
    db: Session,
    battle: BattleInstance,
    gimmick: BattlefieldGimmick,
) -> list[BattleCombatant]:
    query = db.query(BattleCombatant).filter(
        BattleCombatant.battle_id == battle.battle_id,
        BattleCombatant.state == "ACTIVE",
    )

    beneficiary = str(gimmick.beneficiary or "BOTH").upper().strip()
    if beneficiary == "ALLY":
        query = query.filter(BattleCombatant.side == "ALLY")
    elif beneficiary == "ENEMY":
        query = query.filter(BattleCombatant.side == "ENEMY")

    return (
        query
        .order_by(BattleCombatant.join_order.asc(), BattleCombatant.combatant_id.asc())
        .all()
    )


def _append_gimmick_log(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    target_combatant_id: int | None,
    result_type: str,
    damage_value: int,
    hp_after: int,
    narrative_result: str,
    applied_statuses: list[str] | None = None,
) -> None:
    create_battle_action_log(
        db,
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=None,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=target_combatant_id,
        result_type=result_type,
        hit_success=result_type != "MISS",
        crit_success=False,
        guard_success=False,
        evade_success=False,
        damage_value=damage_value,
        hp_after=hp_after,
        applied_statuses=applied_statuses or [],
        declared_tactic_text="",
        used_tags=[],
        narrative_result=narrative_result,
    )


def _apply_damage_gimmick(
    db: Session,
    *,
    battle: BattleInstance,
    gimmick: BattlefieldGimmick,
    turn_no: int,
) -> None:
    effect_detail = gimmick.read_effect_detail()
    damage_value = max(1, int(effect_detail.get("amount", 1) or 1))
    targets = _select_gimmick_targets(db, battle, gimmick)

    for target in targets:
        target.hp_current = max(0, target.hp_current - damage_value)
        if target.hp_current <= 0:
            target.state = "DOWN"
        db.add(target)
        _append_gimmick_log(
            db,
            battle_id=battle.battle_id,
            turn_no=turn_no,
            actor_combatant_id=target.combatant_id,
            target_combatant_id=target.combatant_id,
            result_type="GIMMICK",
            damage_value=damage_value,
            hp_after=target.hp_current,
            narrative_result=(
                f"戦場ギミック「{gimmick.name}」が発動し、{target.display_name}に"
                f"{damage_value}ダメージを与えた。"
            ),
        )


def _apply_visibility_change_gimmick(
    db: Session,
    *,
    battle: BattleInstance,
    gimmick: BattlefieldGimmick,
    turn_no: int,
) -> None:
    effect_detail = gimmick.read_effect_detail()
    visibility_level = str(effect_detail.get("visibility_level", "obscured")).strip() or "obscured"
    _set_battle_visibility_level(battle, visibility_level)
    db.add(battle)

    combatants = get_combatants_for_battle(db, battle.battle_id)
    if not combatants:
        return

    actor = combatants[0]
    _append_gimmick_log(
        db,
        battle_id=battle.battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor.combatant_id,
        target_combatant_id=None,
        result_type="GIMMICK",
        damage_value=0,
        hp_after=actor.hp_current,
        narrative_result=(
            f"戦場ギミック「{gimmick.name}」により視界が{visibility_level}へ変化した。"
        ),
    )


def apply_battlefield_gimmicks_for_timing(
    db: Session,
    *,
    battle_id: int,
    timing: str,
    turn_no: int,
) -> None:
    battle = get_battle(db, battle_id)
    if battle.battlefield_id is None:
        return

    battlefield = get_battlefield_for_battle(db, battle)
    if battlefield is None:
        return

    gimmicks = get_enabled_gimmicks_for_battle(db, battle)
    if not gimmicks:
        return

    for gimmick in gimmicks:
        if not _gimmick_matches_timing(battle, gimmick, timing=timing, turn_no=turn_no):
            continue

        effect_type = str(gimmick.effect_type or "").upper().strip()
        if effect_type == "DAMAGE":
            _apply_damage_gimmick(db, battle=battle, gimmick=gimmick, turn_no=turn_no)
        elif effect_type == "VISIBILITY_CHANGE":
            _apply_visibility_change_gimmick(db, battle=battle, gimmick=gimmick, turn_no=turn_no)
        else:
            continue

        if str(gimmick.repeat_rule or "ONCE").upper().strip() == "ONCE":
            _mark_gimmick_fired_once(battle, gimmick.gimmick_id)
        db.add(battle)

    db.commit()


def get_active_combatants_for_side(
    db: Session,
    battle_id: int,
    side: str,
) -> list[BattleCombatant]:
    return (
        db.query(BattleCombatant)
        .filter(
            BattleCombatant.battle_id == battle_id,
            BattleCombatant.side == side,
            BattleCombatant.state == "ACTIVE",
        )
        .order_by(BattleCombatant.spd.desc(), BattleCombatant.combatant_id.asc())
        .all()
    )


# =========================
# 行動済み管理
# =========================

def reset_turn_state_for_battle(db: Session, battle_id: int) -> None:
    combatants = get_combatants_for_battle(db, battle_id)
    for combatant in combatants:
        clear_acted_this_turn(combatant)
        reduce_cooldowns_for_combatant(combatant)
        db.add(combatant)
    db.commit()


def _consume_idle_stun_turns_before_advance(db: Session, battle_id: int, turn_no: int) -> None:
    combatants = get_combatants_for_battle(db, battle_id)
    for combatant in combatants:
        if combatant.state != "ACTIVE":
            continue
        if has_acted_this_turn(combatant):
            continue
        if not consume_stun_turn(combatant):
            continue

        mark_acted_this_turn(combatant)
        db.add(combatant)
        create_battle_action_log(
            db,
            battle_id=battle_id,
            turn_no=turn_no,
            declaration_id=None,
            actor_combatant_id=combatant.combatant_id,
            target_combatant_id=combatant.combatant_id,
            result_type="STATUS",
            hit_success=False,
            crit_success=False,
            guard_success=False,
            evade_success=False,
            damage_value=0,
            hp_after=combatant.hp_current,
            applied_statuses=["stun"],
            declared_tactic_text="",
            used_tags=[],
            narrative_result=f"{combatant.display_name}はスタンで行動できなかった。",
        )
    db.commit()


def apply_turn_start_statuses_for_battle(db: Session, battle_id: int, turn_no: int) -> None:
    combatants = get_combatants_for_battle(db, battle_id)
    for combatant in combatants:
        events = resolve_turn_start_statuses_for_combatant(combatant)
        db.add(combatant)
        for event in events:
            create_battle_action_log(
                db,
                battle_id=battle_id,
                turn_no=turn_no,
                declaration_id=None,
                actor_combatant_id=combatant.combatant_id,
                target_combatant_id=combatant.combatant_id,
                result_type="STATUS",
                hit_success=True,
                crit_success=False,
                guard_success=False,
                evade_success=False,
                damage_value=event["damage_value"],
                hp_after=event["hp_after"],
                applied_statuses=[event["status_key"]],
                declared_tactic_text="",
                used_tags=[],
                narrative_result=event["narrative_result"],
            )
    db.commit()


# =========================
# 勝敗判定
# =========================

def evaluate_battle_state(db: Session, battle_id: int) -> str:
    battle = get_battle(db, battle_id)

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
        finalize_battle_outcome_if_needed(db, battle_id)
    return battle.state


# =========================
# 行動順
# =========================

def get_turn_order(db: Session, battle_id: int) -> dict[str, Any]:
    battle = get_battle(db, battle_id)
    combatants = get_combatants_for_battle(db, battle_id)

    return {
        "battle_id": battle.battle_id,
        "turn_no": battle.turn_no,
        "order": [
            {
                "combatant_id": c.combatant_id,
                "display_name": c.display_name,
                "side": c.side,
                "spd": c.spd,
                "state": c.state,
                "has_acted": has_acted_this_turn(c),
            }
            for c in combatants
        ],
    }


# =========================
# 自動行動対象
# =========================

def _is_auto_controlled(combatant: BattleCombatant) -> bool:
    controller_type = str(combatant.snapshot_json or "")
    # snapshot 内判定は resolver / ai_service 側に集約でも良いが、
    # ここでは軽量に文字列包含でなく、簡易に PLAYER フラグだけ避ける
    # 後で API から初期化される controller_type を使う
    from app.services.simple_battle_resolver import _read_controller_type
    return _read_controller_type(combatant) != "PLAYER"


def get_auto_controlled_allies(db: Session, battle_id: int) -> list[BattleCombatant]:
    allies = get_active_combatants_for_side(db, battle_id, "ALLY")
    return [c for c in allies if _is_auto_controlled(c)]


def get_auto_controlled_enemies(db: Session, battle_id: int) -> list[BattleCombatant]:
    enemies = get_active_combatants_for_side(db, battle_id, "ENEMY")
    return [c for c in enemies if _is_auto_controlled(c)]


# =========================
# AIフェーズ
# =========================

def _run_auto_actions_for_group(
    db: Session,
    *,
    battle: BattleInstance,
    combatants: list[BattleCombatant],
) -> int:
    acted_count = 0

    for combatant in combatants:
        battle = get_battle(db, battle.battle_id)
        if battle.state != "ACTIVE":
            break

        # 最新状態取得
        actor = (
            db.query(BattleCombatant)
            .filter(BattleCombatant.combatant_id == combatant.combatant_id)
            .first()
        )
        if not actor:
            continue
        if actor.state != "ACTIVE":
            continue
        if has_acted_this_turn(actor):
            continue
        if has_status(actor, "stun"):
            consume_stun_turn(actor)
            mark_acted_this_turn(actor)
            db.add(actor)
            db.commit()
            create_battle_action_log(
                db,
                battle_id=battle.battle_id,
                turn_no=battle.turn_no,
                declaration_id=None,
                actor_combatant_id=actor.combatant_id,
                target_combatant_id=actor.combatant_id,
                result_type="STATUS",
                hit_success=False,
                crit_success=False,
                guard_success=False,
                evade_success=False,
                damage_value=0,
                hp_after=actor.hp_current,
                applied_statuses=["stun"],
                declared_tactic_text="",
                used_tags=[],
                narrative_result=f"{actor.display_name}はスタンで行動できない。",
            )
            continue

        decision = decide_action_for_combatant(
            db,
            battle=battle,
            actor=actor,
        )

        result = resolve_ai_decision(
            db,
            battle_id=battle.battle_id,
            turn_no=battle.turn_no,
            actor_combatant_id=actor.combatant_id,
            decision=decision,
        )

        # WAIT などで declaration が無い場合も、行動した扱いにはしない設計もあり得るが、
        # 今回は resolve できた行動だけカウント
        if result is not None:
            acted_count += 1

        current_state = evaluate_battle_state(db, battle.battle_id)
        if current_state != "ACTIVE":
            break

    return acted_count


def run_ally_ai_phase(db: Session, battle_id: int) -> dict[str, Any]:
    battle = get_battle(db, battle_id)
    if battle.state != "ACTIVE":
        return {
            "battle_state": battle.state,
            "acted_ally_count": 0,
        }

    allies = get_auto_controlled_allies(db, battle_id)
    acted_ally_count = _run_auto_actions_for_group(
        db,
        battle=battle,
        combatants=allies,
    )

    battle = get_battle(db, battle_id)
    return {
        "battle_state": battle.state,
        "acted_ally_count": acted_ally_count,
    }


def run_enemy_phase(db: Session, battle_id: int) -> dict[str, Any]:
    battle = get_battle(db, battle_id)
    if battle.state != "ACTIVE":
        return {
            "battle_state": battle.state,
            "acted_enemy_count": 0,
        }

    enemies = get_auto_controlled_enemies(db, battle_id)
    acted_enemy_count = _run_auto_actions_for_group(
        db,
        battle=battle,
        combatants=enemies,
    )

    battle = get_battle(db, battle_id)
    return {
        "battle_state": battle.state,
        "acted_enemy_count": acted_enemy_count,
    }


# =========================
# ターン進行
# =========================

def advance_turn_and_run_auto_phases(db: Session, battle_id: int) -> dict[str, Any]:
    battle = get_battle(db, battle_id)

    if battle.state != "ACTIVE":
        finalize_battle_outcome_if_needed(db, battle_id)
        battle = get_battle(db, battle_id)
        return {
            "battle_id": battle.battle_id,
            "turn_no": battle.turn_no,
            "state": battle.state,
            "acted_ally_count": 0,
            "acted_enemy_count": 0,
        }

    _consume_idle_stun_turns_before_advance(db, battle_id, battle.turn_no)
    battle = get_battle(db, battle_id)

    battle.turn_no += 1
    db.add(battle)
    db.commit()
    db.refresh(battle)

    reset_turn_state_for_battle(db, battle_id)
    apply_turn_start_statuses_for_battle(db, battle_id, battle.turn_no)
    apply_battlefield_gimmicks_for_timing(
        db,
        battle_id=battle_id,
        timing="TURN_START",
        turn_no=battle.turn_no,
    )

    battle_state = evaluate_battle_state(db, battle_id)
    if battle_state != "ACTIVE":
        battle = get_battle(db, battle_id)
        return {
            "battle_id": battle.battle_id,
            "turn_no": battle.turn_no,
            "state": battle.state,
            "acted_ally_count": 0,
            "acted_enemy_count": 0,
        }

    # 味方NPC → 敵 の順で自動行動
    ally_result = run_ally_ai_phase(db, battle_id)
    battle = get_battle(db, battle_id)

    enemy_result = {"acted_enemy_count": 0, "battle_state": battle.state}
    if battle.state == "ACTIVE":
        enemy_result = run_enemy_phase(db, battle_id)

    battle = get_battle(db, battle_id)
    if battle.state == "ACTIVE":
        apply_battlefield_gimmicks_for_timing(
            db,
            battle_id=battle_id,
            timing="TURN_END",
            turn_no=battle.turn_no,
        )
        evaluate_battle_state(db, battle_id)

    battle = get_battle(db, battle_id)
    return {
        "battle_id": battle.battle_id,
        "turn_no": battle.turn_no,
        "state": battle.state,
        "acted_ally_count": ally_result["acted_ally_count"],
        "acted_enemy_count": enemy_result["acted_enemy_count"],
    }


# =========================
# 戦闘終了時の軽い成長反映
# =========================

def finalize_battle_growth(db: Session, battle_id: int) -> None:
    finalize_battle_outcome_if_needed(db, battle_id)


def finalize_battle_outcome_if_needed(db: Session, battle_id: int) -> bool:
    battle = get_battle(db, battle_id)
    if battle.state not in {"RESOLVED", "DEFEATED"}:
        return False
    if _is_battle_outcome_finalized(battle):
        return False

    combatants = get_combatants_for_battle(db, battle_id)
    for combatant in combatants:
        survived = combatant.state == "ACTIVE"
        acted = has_acted_this_turn(combatant)
        followed_order = bool(
            from_snapshot_order_applied(combatant)
        )

        apply_post_battle_progression(
            combatant,
            battle_state=battle.state,
            survived=survived,
            acted=acted,
            followed_order=followed_order,
        )
        if combatant.side == "ALLY" and not combatant.is_player_controlled:
            upsert_world_combatant_progress(
                db,
                world_id=battle.world_id,
                battle_id=battle.battle_id,
                combatant=combatant,
            )
        db.add(combatant)

    world_result = apply_battle_resolution_world_progress(
        db,
        world_id=battle.world_id,
        battle_id=battle.battle_id,
        battle_state=battle.state,
    )
    _mark_battle_outcome_finalized(
        battle,
        quest_progress_delta=int(world_result.get("quest_progress_delta", 0) or 0),
        main_quest_progress_delta=int(world_result.get("main_quest_progress_delta", 0) or 0),
        demon_score_delta=int(world_result.get("demon_score_delta", 0) or 0),
    )
    db.add(battle)
    db.commit()
    return True


def from_snapshot_order_applied(combatant: BattleCombatant) -> bool:
    from app.services.simple_battle_resolver import _read_snapshot
    return bool(_read_snapshot(combatant, "order_applied_this_turn", False))
