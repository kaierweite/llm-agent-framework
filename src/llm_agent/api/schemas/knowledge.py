from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    chat_provider: Optional[str] = Field(None, max_length=100)
    chat_model: Optional[str] = Field(None, max_length=200)


class KnowledgeBaseRename(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class KnowledgeBaseQuery(BaseModel):
    question: str = Field(..., min_length=1)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    upload_status: str
    error_message: Optional[str] = None
    created_at: datetime


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    document_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    document_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentResponse]


class PaginatedKnowledgeBases(BaseModel):
    items: List[KnowledgeBaseResponse]
    total: int
    page: int
    page_size: int


class PaginatedDocuments(BaseModel):
    items: List[DocumentResponse]
    total: int
    page: int
    page_size: int
