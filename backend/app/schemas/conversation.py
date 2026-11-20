from typing import List, Optional, Any
from pydantic import BaseModel, Field

class AttachedDocumentMeta(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    document_name: str = Field(..., description="Original filename of the PDF")
    size_bytes: int = Field(0, description="File size in bytes")
    upload_timestamp: str = Field(..., description="Timestamp of attachment")
    status: str = Field("processed", description="Document processing status")

class ConversationMessage(BaseModel):
    id: str = Field(..., description="Message identifier")
    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message text")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sources: Optional[List[Any]] = Field(default_factory=list)
    attached_files: Optional[List[AttachedDocumentMeta]] = Field(default_factory=list)
    status: Optional[str] = Field("completed", description="Response status")

class ConversationDetail(BaseModel):
    id: str = Field(..., description="Unique conversation ID")
    user_id: str = Field("default_user", description="Owner user ID")
    title: str = Field("New Chat", description="Conversation title")
    created_at: str = Field(..., description="Creation ISO timestamp")
    updated_at: str = Field(..., description="Last update ISO timestamp")
    documents: List[AttachedDocumentMeta] = Field(default_factory=list, description="Attached PDFs")
    messages: List[ConversationMessage] = Field(default_factory=list, description="Chat messages")

class ConversationSummary(BaseModel):
    id: str = Field(..., description="Unique conversation ID")
    user_id: str = Field("default_user", description="Owner user ID")
    title: str = Field("New Chat", description="Conversation title")
    created_at: str = Field(..., description="Creation ISO timestamp")
    updated_at: str = Field(..., description="Last update ISO timestamp")
    message_count: int = Field(0, description="Number of messages")
    document_count: int = Field(0, description="Number of attached documents")
    documents: List[AttachedDocumentMeta] = Field(default_factory=list, description="Attached PDFs summary")

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional title")
    document_ids: Optional[List[str]] = Field(default_factory=list, description="Optional initial documents to attach")
