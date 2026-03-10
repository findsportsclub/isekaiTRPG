from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattleActionLog(Base):
    __tablename__ = "battle_action_logs"

    action_log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    battle_id: Mapped[int] = mapped_column(
        ForeignKey("battle_instances.battle_id"),
        nullable=False,
        index=True,
    )

    turn_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    declaration_id: Mapped[int] = mapped_column(
        ForeignKey("battle_action_declarations.declaration_id"),
        nullable=True,
        index=True,
    )

    actor_combatant_id: Mapped[int] = mapped_column(
        ForeignKey("battle_combatants.combatant_id"),
        nullable=False,
        index=True,
    )

    target_combatant_id: Mapped[int] = mapped_column(
        ForeignKey("battle_combatants.combatant_id"),
        nullable=True,
        index=True,
    )

    result_type: Mapped[str] = mapped_column(String(50), nullable=False, default="HIT")

    hit_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    crit_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    guard_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evade_success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    damage_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hp_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    applied_status_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    declared_tactic_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    used_tags_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    narrative_result: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )