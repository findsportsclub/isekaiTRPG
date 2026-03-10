from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattleActionDeclaration(Base):
    __tablename__ = "battle_action_declarations"

    declaration_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    battle_id: Mapped[int] = mapped_column(
        ForeignKey("battle_instances.battle_id"),
        nullable=False,
        index=True,
    )

    turn_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    actor_combatant_id: Mapped[int] = mapped_column(
        ForeignKey("battle_combatants.combatant_id"),
        nullable=False,
        index=True,
    )

    action_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ATTACK")

    primary_target_combatant_id: Mapped[int] = mapped_column(
        ForeignKey("battle_combatants.combatant_id"),
        nullable=True,
        index=True,
    )

    secondary_target_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    skill_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    item_id: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    declared_tactic_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    parsed_tags_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
    )

    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW")

    resolution_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
    )