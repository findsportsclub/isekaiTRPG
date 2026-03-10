from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldRelationEdge(Base):
    __tablename__ = "world_relation_edges"
    __table_args__ = (
        UniqueConstraint("world_id", "actor_key", "target_key", name="uq_world_relation_edge"),
    )

    relation_edge_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False, index=True)
    actor_key: Mapped[str] = mapped_column(String(100), nullable=False, default="hero")
    target_key: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")

    relation_frame: Mapped[str] = mapped_column(String(50), nullable=False, default="communal")
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="acquaintance")
    attachment_style: Mapped[str] = mapped_column(String(50), nullable=False, default="secure")
    support_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    bond_metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    story_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    story_heat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    interaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_story_seed: Mapped[str] = mapped_column(String(100), nullable=False, default="none")
    last_updated_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="init")
