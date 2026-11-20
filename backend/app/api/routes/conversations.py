import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, status

from app.schemas.conversation import (
    ConversationSummary,
    ConversationDetail,
    CreateConversationRequest
)
from app.services.conversation_service import conversation_service
from app.api.deps import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations"])

@router.get("", response_model=List[ConversationSummary], status_code=status.HTTP_200_OK)
async def list_conversations(
    user_id: str = Depends(get_current_user_id)
):
    """Lists all active and previous conversations for the authenticated user."""
    return conversation_service.list_conversations(user_id=user_id)

@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Creates a new conversation session with optional initial attached documents."""
    return conversation_service.create_conversation(
        user_id=user_id,
        title=request.title,
        document_ids=request.document_ids
    )

@router.get("/{conversation_id}", response_model=ConversationDetail, status_code=status.HTTP_200_OK)
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Retrieves full conversation details, history, and attached document context."""
    return conversation_service.get_conversation(conversation_id, user_id=user_id)

@router.delete("/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Deletes a conversation session and cleans up its context."""
    success = conversation_service.delete_conversation(conversation_id, user_id=user_id)
    return {"status": "deleted" if success else "not_found", "conversation_id": conversation_id}

@router.post("/{conversation_id}/documents/{document_id}", response_model=ConversationDetail, status_code=status.HTTP_200_OK)
async def attach_document_to_conversation(
    conversation_id: str,
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Associates a PDF document with the conversation.
    Subsequent questions in this conversation will automatically retrieve from this document.
    """
    return conversation_service.attach_document(
        conv_id=conversation_id,
        document_id=document_id,
        user_id=user_id
    )

@router.delete("/{conversation_id}/documents/{document_id}", response_model=ConversationDetail, status_code=status.HTTP_200_OK)
async def detach_document_from_conversation(
    conversation_id: str,
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Removes a PDF document from the conversation's active retrieval context.
    """
    return conversation_service.detach_document(
        conv_id=conversation_id,
        document_id=document_id,
        user_id=user_id
    )
