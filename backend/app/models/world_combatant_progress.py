from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldCombatantProgress(Base):
    __tablename__ = "world_combatant_progress"
    __table_args__ = (
        UniqueConstraint("world_id", "entity_id", name="uq_world_combatant_progress"),
    )

    progress_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    growth_stats_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    relationship_modifiers_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    updated_from_battle_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
