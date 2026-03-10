from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.battle_action_log import BattleActionLog


def create_battle_action_log(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    declaration_id: int | None,
    actor_combatant_id: int,
    target_combatant_id: int | None = None,
    result_type: str = "HIT",
    hit_success: bool = False,
    crit_success: bool = False,
    guard_success: bool = False,
    evade_success: bool = False,
    damage_value: int = 0,
    hp_after: int = 0,
    applied_statuses: list[str] | None = None,
    declared_tactic_text: str = "",
    used_tags: list[str] | None = None,
    narrative_result: str = "",
) -> BattleActionLog:
    """
    戦闘行動の結果ログを保存する。
    """
    action_log = BattleActionLog(
        battle_id=battle_id,
        turn_no=turn_no,
        declaration_id=declaration_id,
        actor_combatant_id=actor_combatant_id,
        target_combatant_id=target_combatant_id,
        result_type=result_type,
        hit_success=hit_success,
        crit_success=crit_success,
        guard_success=guard_success,
        evade_success=evade_success,
        damage_value=damage_value,
        hp_after=hp_after,
        applied_status_json=json.dumps(applied_statuses or [], ensure_ascii=False),
        declared_tactic_text=declared_tactic_text,
        used_tags_json=json.dumps(used_tags or [], ensure_ascii=False),
        narrative_result=narrative_result,
    )

    db.add(action_log)
    db.commit()
    db.refresh(action_log)

    return action_log