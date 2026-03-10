from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class World(Base):
    __tablename__ = "worlds"

    world_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    world_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hero_name: Mapped[str] = mapped_column(String(255), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    era: Mapped[str] = mapped_column(String(100), nullable=False, default="DUNGEON_AGE")
    current_location: Mapped[str] = mapped_column(String(255), nullable=False, default="はじまりの村")
