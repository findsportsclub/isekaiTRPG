from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.battle_action_declaration import BattleActionDeclaration
from app.services.tactic_parser import parse_tactic_tags


def create_battle_action_declaration(
    db: Session,
    *,
    battle_id: int,
    turn_no: int,
    actor_combatant_id: int,
    action_type: str,
    primary_target_combatant_id: int | None = None,
    secondary_target_ids: list[int] | None = None,
    skill_id: str = "",
    item_id: str = "",
    declared_tactic_text: str = "",
    risk_level: str = "LOW",
) -> BattleActionDeclaration:
    """
    戦闘行動宣言を作成し、自由記述戦術からタグを抽出して保存する。
    """
    parsed_tags = parse_tactic_tags(declared_tactic_text)

    declaration = BattleActionDeclaration(
        battle_id=battle_id,
        turn_no=turn_no,
        actor_combatant_id=actor_combatant_id,
        action_type=action_type,
        primary_target_combatant_id=primary_target_combatant_id,
        secondary_target_json=json.dumps(secondary_target_ids or [], ensure_ascii=False),
        skill_id=skill_id,
        item_id=item_id,
        declared_tactic_text=declared_tactic_text,
        parsed_tags_json=json.dumps(parsed_tags, ensure_ascii=False),
        risk_level=risk_level,
        resolution_status="PENDING",
    )

    db.add(declaration)
    db.commit()
    db.refresh(declaration)

    return declaration