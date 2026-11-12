from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str


class NumberCreate(BaseModel):
    session_name: str = Field(pattern=r"^[a-z0-9_-]{2,40}$")
    label: str = Field(min_length=1, max_length=120)


class NumberOut(ORM):
    id: int
    session_name: str
    label: str
    phone: str | None
    provider: str
    status: str
    status_changed_at: datetime


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    position: int = 0
    is_won: bool = False
    is_lost: bool = False


class StageOut(ORM):
    id: int
    name: str
    position: int
    is_won: bool
    is_lost: bool


class ContactOut(ORM):
    id: int
    chat_id: str
    name: str | None
    phone: str | None


class ConversationOut(ORM):
    id: int
    number_id: int
    contact: ContactOut
    stage_id: int | None
    assigned_to: int | None
    status: str
    unread_count: int
    last_message_at: datetime | None
    last_message_preview: str | None
    first_inbound_at: datetime | None
    first_response_at: datetime | None


class ConversationUpdate(BaseModel):
    stage_id: int | None = None
    assigned_to: int | None = None
    status: str | None = Field(default=None, pattern=r"^(open|closed)$")


class MessageOut(ORM):
    id: int
    conversation_id: int
    direction: str
    body: str
    has_media: bool
    ack: int
    sent_by: int | None
    created_at: datetime


class SendMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
