from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattleCombatant(Base):
    __tablename__ = "battle_combatants"

    combatant_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    battle_id: Mapped[int] = mapped_column(
        ForeignKey("battle_instances.battle_id"),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="NPC")
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    side: Mapped[str] = mapped_column(String(20), nullable=False, default="ENEMY")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="FRONT")
    join_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    hp_current: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    hp_max: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    mp_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mp_max: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    atk: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    defense: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mag: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    res: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spd: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    hit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eva: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    guard_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    initiative_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_player_controlled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    snapshot_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )