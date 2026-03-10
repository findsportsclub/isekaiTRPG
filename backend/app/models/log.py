from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Log(Base):
    __tablename__ = "logs"

    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.world_id"), nullable=False)
    log_type: Mapped[str] = mapped_column(String(50), nullable=False, default="action")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)