from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldRelationshipState(Base):
    __tablename__ = "world_relationship_states"
    __table_args__ = (
        UniqueConstraint("world_id", "target_key", name="uq_world_relationship_target"),
    )

    relationship_state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False, index=True)
    target_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    affinity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reaction_label: Mapped[str] = mapped_column(String(50), nullable=False, default="neutral")
    reaction_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_interaction_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")
