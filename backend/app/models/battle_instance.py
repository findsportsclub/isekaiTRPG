from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class BattleInstance(Base):
    __tablename__ = "battle_instances"

    battle_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    world_id: Mapped[int] = mapped_column(
        ForeignKey("worlds.world_id"),
        nullable=False,
        index=True,
    )

    location_id: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    battlefield_id: Mapped[int] = mapped_column(
        ForeignKey("battlefields.battlefield_id"),
        nullable=True,
        index=True,
    )

    battle_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ENCOUNTER")
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default="MANUAL")
    source_ref_id: Mapped[str] = mapped_column(String(100), nullable=False, default="none")

    state: Mapped[str] = mapped_column(String(50), nullable=False, default="PREPARE")
    turn_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    objective_type: Mapped[str] = mapped_column(String(50), nullable=False, default="DEFEAT")

    objective_snapshot_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )

    victory_condition_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"type":"defeat_all_enemies"}',
    )
    defeat_condition_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{"type":"player_down"}',
    )

    battle_difficulty_snapshot_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='{}',
    )