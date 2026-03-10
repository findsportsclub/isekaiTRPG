from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldTendencyState(Base):
    __tablename__ = "world_tendency_states"
    __table_args__ = (
        UniqueConstraint("world_id", "actor_key", name="uq_world_tendency_actor"),
    )

    tendency_state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False, index=True)
    actor_key: Mapped[str] = mapped_column(String(100), nullable=False, default="hero")
    tendency_scores_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_updated_reason: Mapped[str] = mapped_column(String(100), nullable=False, default="init")
    update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
