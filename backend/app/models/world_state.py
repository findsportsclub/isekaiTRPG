from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class WorldState(Base):
    __tablename__ = "world_states"

    state_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), unique=True, nullable=False)

    dungeon_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    faction_score: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    demon_score: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    security_score: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    gold: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    tax_debt: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    meal_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    main_event_title: Mapped[str] = mapped_column(String(255), nullable=False, default="北坑道の異変")
    main_event_state: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")
    quest_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    housing_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="lodging")
