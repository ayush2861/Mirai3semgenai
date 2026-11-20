from fastapi import APIRouter, Depends, status
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat_service
from app.api.deps import get_current_user_id

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def handle_chat_message(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    RAG Chat endpoint:
    Retrieves evidence from user-authorized documents using hybrid search (ChromaDB + BM25)
    and generates a grounded answer with verified citations via Google Gemini API.
    """
    return await chat_service.process_chat_message(request, user_id=user_id)
