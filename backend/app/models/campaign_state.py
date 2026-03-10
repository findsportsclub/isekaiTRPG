from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CampaignState(Base):
    __tablename__ = "campaign_states"

    campaign_state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(
        ForeignKey("worlds.world_id"),
        unique=True,
        nullable=False,
        index=True,
    )

    current_phase: Mapped[str] = mapped_column(String(50), nullable=False, default="HUB")
    day_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    time_slot: Mapped[str] = mapped_column(String(30), nullable=False, default="MORNING")

    narrative_state_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    phase_context_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
