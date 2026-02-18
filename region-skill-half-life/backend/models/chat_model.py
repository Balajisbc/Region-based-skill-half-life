"""Persistence model for AI assistant conversations and interaction history."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
	from models.user_model import User


class ChatHistory(Base):
	"""Conversation history record mapped to a user account and regional skill context."""

	__tablename__ = "chat_history"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	user_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("users.id", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
	country: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
	city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
	skill: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
	message: Mapped[str] = mapped_column(Text, nullable=False)
	response: Mapped[str] = mapped_column(Text, nullable=False)
	timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

	user: Mapped["User"] = relationship("User", back_populates="chats")


Chat = ChatHistory
