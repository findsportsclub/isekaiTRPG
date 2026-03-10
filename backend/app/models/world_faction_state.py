from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldFactionState(Base):
    __tablename__ = "world_faction_states"
    __table_args__ = (
        UniqueConstraint("world_id", "faction_key", name="uq_world_faction_key"),
    )

    faction_state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False, index=True)
    faction_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="guild")
    influence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    power_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cohesion_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tension_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stance_label: Mapped[str] = mapped_column(String(50), nullable=False, default="neutral")
    notes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_incident_hint: Mapped[str] = mapped_column(String(255), nullable=False, default="")
