from typing import Optional
from pydantic import BaseModel

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str = "uploaded"
    message: str = "Document uploaded successfully"

class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    size_bytes: int
    content_type: str = "application/pdf"
    status: str = "uploaded"
    user_id: Optional[str] = "default_user"
    uploaded_at: str

class DocumentDeleteResponse(BaseModel):
    document_id: str
    status: str = "deleted"
    message: str = "Document deleted successfully"
