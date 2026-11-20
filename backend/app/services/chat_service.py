import logging
from typing import Optional
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai.ai_service import ai_service

logger = logging.getLogger(__name__)

class ChatService:
    @staticmethod
    async def process_chat_message(request: ChatRequest, user_id: str = "default_user") -> ChatResponse:
        """
        Executes grounded RAG response generation using Phase 4 hybrid retrieval
        and Phase 5 Gemini AI synthesis.
        """
        logger.info(
            f"Processing chat inquiry | user: {user_id} | conv: {request.conversation_id} | "
            f"message: {request.message[:60]}..."
        )

        return await ai_service.generate_rag_answer(
            question=request.message,
            conversation_id=request.conversation_id,
            user_id=user_id,
            document_ids=request.document_ids,
            top_k=request.top_k or 5
        )

chat_service = ChatService()
