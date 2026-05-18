from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class ConversationCreate(BaseModel):
    title: Optional[str] = Field("新对话", max_length=255)
    knowledge_base_id: Optional[str] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    knowledge_base_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    token_count: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime


class ConversationListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    knowledge_base_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    knowledge_base_id: Optional[str] = None


class PaginatedConversations(BaseModel):
    items: List[ConversationListItem]
    total: int
    page: int
    page_size: int


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
