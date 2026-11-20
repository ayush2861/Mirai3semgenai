from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator

class ChatRequest(BaseModel):
    message: str = Field(..., description="User infrastructure / SRE runbook inquiry")
    conversation_id: Optional[str] = Field(None, description="Optional active conversation ID")
    document_ids: Optional[List[str]] = Field(None, description="Optional document IDs scope")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Max chunks to retrieve")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or blank whitespace.")
        return v.strip()

class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    answer: Optional[str] = None
    sources: List[Any] = Field(default_factory=list)
    status: str = "pending"
