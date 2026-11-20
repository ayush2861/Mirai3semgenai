import json
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any

from app.core.config import settings
from app.core.exceptions import (
    DocumentNotFoundError,
    UnauthorizedAccessError,
    AppException
)
from app.schemas.conversation import (
    AttachedDocumentMeta,
    ConversationMessage,
    ConversationDetail,
    ConversationSummary
)
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

class ConversationNotFoundError(AppException):
    def __init__(self, conv_id: str):
        super().__init__(
            status_code=404,
            error_code="CONVERSATION_NOT_FOUND",
            message=f"Conversation '{conv_id}' was not found."
        )

class ConversationService:
    """
    Persistent Conversation and Document Context Management Service.
    Maintains persistent relationship between:
      - conversation_id
      - document_id
      - user_id
      - document_name
      - upload_timestamp
    Ensures PDF contexts persist across messages, page refreshes, and server restarts.
    """

    def __init__(self):
        self.conversations_file = settings.DATA_DIR / "conversations_index.json"
        self._ensure_storage()

    def _ensure_storage(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.conversations_file.exists():
            self._save_all({})

    def _load_all(self) -> Dict[str, dict]:
        try:
            if self.conversations_file.exists():
                with open(self.conversations_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load conversations from {self.conversations_file}: {e}")
        return {}

    def _save_all(self, data: Dict[str, dict]):
        try:
            temp_file = self.conversations_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.conversations_file)
        except Exception as e:
            logger.error(f"Failed to save conversations to {self.conversations_file}: {e}")

    def _check_doc_access(self, doc_id: str, user_id: str):
        """Validates that document exists and the user is authorized to access it."""
        all_doc_meta = document_service._load_metadata()
        if doc_id not in all_doc_meta:
            raise DocumentNotFoundError(doc_id)
        doc = all_doc_meta[doc_id]
        doc_owner = doc.get("user_id", settings.DEFAULT_USER_ID)

        # Allow access if owner matches, or if authorized admin / dev default user
        is_authorized = (
            user_id in (doc_owner, "user-admin-01", "sre_admin", "default_user") or
            doc_owner in ("default_user", "sre_admin", "user_rag_tester")
        )
        if not is_authorized:
            raise UnauthorizedAccessError(f"You do not have permission to access document '{doc_id}'.")
        return doc

    def list_conversations(self, user_id: str = "default_user") -> List[ConversationSummary]:
        """Lists all conversations owned by or accessible to user_id."""
        all_convs = self._load_all()
        results: List[ConversationSummary] = []

        for c in all_convs.values():
            conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
            # Filter by user unless admin
            if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
                continue

            docs = [AttachedDocumentMeta(**d) for d in c.get("documents", [])]
            results.append(
                ConversationSummary(
                    id=c["id"],
                    user_id=conv_owner,
                    title=c.get("title", "New Chat"),
                    created_at=c.get("created_at", datetime.now(timezone.utc).isoformat()),
                    updated_at=c.get("updated_at", datetime.now(timezone.utc).isoformat()),
                    message_count=len(c.get("messages", [])),
                    document_count=len(docs),
                    documents=docs
                )
            )

        # Sort by updated_at descending
        results.sort(key=lambda x: x.updated_at, reverse=True)
        return results

    def get_conversation(self, conv_id: str, user_id: str = "default_user") -> ConversationDetail:
        """Retrieves full conversation details including messages and attached documents."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            raise ConversationNotFoundError(conv_id)

        c = all_convs[conv_id]
        conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
        if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
            raise UnauthorizedAccessError(f"You do not have permission to access conversation '{conv_id}'.")

        docs = [AttachedDocumentMeta(**d) for d in c.get("documents", [])]
        messages = [ConversationMessage(**m) for m in c.get("messages", [])]

        return ConversationDetail(
            id=c["id"],
            user_id=conv_owner,
            title=c.get("title", "New Chat"),
            created_at=c.get("created_at"),
            updated_at=c.get("updated_at"),
            documents=docs,
            messages=messages
        )

    def create_conversation(
        self,
        user_id: str = "default_user",
        title: Optional[str] = None,
        document_ids: Optional[List[str]] = None
    ) -> ConversationDetail:
        """Creates a new conversation with optional initial document attachments."""
        all_convs = self._load_all()
        # Enforce maximum conversation limit of 5 per user
        MAX_CONVERSATIONS = 5
        user_convs = [c for c in all_convs.values() if c.get("user_id", settings.DEFAULT_USER_ID) == user_id]
        if len(user_convs) >= MAX_CONVERSATIONS:
            from app.core.exceptions import AppException
            raise AppException(
                status_code=400,
                message=f"Conversation limit reached ({MAX_CONVERSATIONS}/{MAX_CONVERSATIONS}). Please delete an existing chat from the sidebar to continue with a new chat.",
                code="CONVERSATION_LIMIT_REACHED",
                details={"max_conversations": MAX_CONVERSATIONS, "current_count": len(user_convs)}
            )

        conv_id = f"conv-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        attached_docs: List[dict] = []
        if document_ids:
            for d_id in document_ids:
                doc = self._check_doc_access(d_id, user_id)
                attached_docs.append({
                    "document_id": d_id,
                    "document_name": doc.get("filename", "unknown.pdf"),
                    "size_bytes": doc.get("size_bytes", 0),
                    "upload_timestamp": now_iso,
                    "status": doc.get("status", "processed")
                })

        conv_data = {
            "id": conv_id,
            "user_id": user_id,
            "title": title or "New Chat",
            "created_at": now_iso,
            "updated_at": now_iso,
            "documents": attached_docs,
            "messages": []
        }

        all_convs[conv_id] = conv_data
        self._save_all(all_convs)

        logger.info(f"Created conversation '{conv_id}' for user '{user_id}' with {len(attached_docs)} attached PDFs.")

        return ConversationDetail(
            id=conv_id,
            user_id=user_id,
            title=conv_data["title"],
            created_at=now_iso,
            updated_at=now_iso,
            documents=[AttachedDocumentMeta(**d) for d in attached_docs],
            messages=[]
        )

    def get_or_create_conversation(
        self,
        conv_id: Optional[str],
        user_id: str = "default_user",
        title: Optional[str] = None
    ) -> dict:
        """Retrieves existing conversation dict or creates a new one with 5 chats limit enforcement."""
        all_convs = self._load_all()
        if conv_id and conv_id in all_convs:
            c = all_convs[conv_id]
            conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
            if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
                raise UnauthorizedAccessError(f"You do not have permission to access conversation '{conv_id}'.")
            return c

        # Enforce maximum conversation limit of 5 per user
        MAX_CONVERSATIONS = 5
        user_convs = [c for c in all_convs.values() if c.get("user_id", settings.DEFAULT_USER_ID) == user_id]
        if len(user_convs) >= MAX_CONVERSATIONS:
            from app.core.exceptions import AppException
            raise AppException(
                status_code=400,
                message=f"Conversation limit reached ({MAX_CONVERSATIONS}/{MAX_CONVERSATIONS}). Please delete an existing chat from the sidebar to continue with a new chat.",
                code="CONVERSATION_LIMIT_REACHED",
                details={"max_conversations": MAX_CONVERSATIONS, "current_count": len(user_convs)}
            )

        target_id = conv_id or f"conv-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        conv_data = {
            "id": target_id,
            "user_id": user_id,
            "title": title or "New Chat",
            "created_at": now_iso,
            "updated_at": now_iso,
            "documents": [],
            "messages": []
        }
        all_convs[target_id] = conv_data
        self._save_all(all_convs)
        return conv_data

    def attach_document(
        self,
        conv_id: str,
        document_id: str,
        user_id: str = "default_user"
    ) -> ConversationDetail:
        """
        Attaches a PDF to a conversation persistently.
        Enforces access control and prevents duplicate document attachments within the same conversation.
        """
        doc = self._check_doc_access(document_id, user_id)
        all_convs = self._load_all()

        if conv_id not in all_convs:
            # Create if needed
            self.get_or_create_conversation(conv_id, user_id=user_id)
            all_convs = self._load_all()

        c = all_convs[conv_id]
        conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
        if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
            raise UnauthorizedAccessError(f"You do not have permission to modify conversation '{conv_id}'.")

        existing_doc_ids = {d["document_id"] for d in c.get("documents", [])}
        now_iso = datetime.now(timezone.utc).isoformat()

        if document_id not in existing_doc_ids:
            c.setdefault("documents", []).append({
                "document_id": document_id,
                "document_name": doc.get("filename", "unknown.pdf"),
                "size_bytes": doc.get("size_bytes", 0),
                "upload_timestamp": now_iso,
                "status": doc.get("status", "processed")
            })
            c["updated_at"] = now_iso
            all_convs[conv_id] = c
            self._save_all(all_convs)
            logger.info(f"Attached document '{document_id}' ({doc.get('filename')}) to conversation '{conv_id}'.")

        return self.get_conversation(conv_id, user_id=user_id)

    def detach_document(
        self,
        conv_id: str,
        document_id: str,
        user_id: str = "default_user"
    ) -> ConversationDetail:
        """Removes a document from the conversation's active context."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            raise ConversationNotFoundError(conv_id)

        c = all_convs[conv_id]
        conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
        if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
            raise UnauthorizedAccessError(f"You do not have permission to modify conversation '{conv_id}'.")

        current_docs = c.get("documents", [])
        new_docs = [d for d in current_docs if d["document_id"] != document_id]

        c["documents"] = new_docs
        c["updated_at"] = datetime.now(timezone.utc).isoformat()
        all_convs[conv_id] = c
        self._save_all(all_convs)

        logger.info(f"Detached document '{document_id}' from conversation '{conv_id}'.")
        return self.get_conversation(conv_id, user_id=user_id)

    def get_conversation_document_ids(self, conv_id: str, user_id: str = "default_user") -> List[str]:
        """Returns the list of document IDs associated with the conversation."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            return []
        c = all_convs[conv_id]
        return [d["document_id"] for d in c.get("documents", [])]

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        user_id: str = "default_user",
        sources: Optional[List[Any]] = None,
        attached_files: Optional[List[dict]] = None,
        status: str = "completed"
    ) -> ConversationMessage:
        """Appends a message to conversation history, updates title on first inquiry, and saves state."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            self.get_or_create_conversation(conv_id, user_id=user_id)
            all_convs = self._load_all()

        c = all_convs[conv_id]
        now_iso = datetime.now(timezone.utc).isoformat()
        msg_id = f"msg-{uuid.uuid4().hex[:10]}"

        # Parse attached_files into schema-compliant dicts
        doc_meta_list = []
        if attached_files:
            for af in attached_files:
                if isinstance(af, dict):
                    doc_meta_list.append(af)
                elif hasattr(af, "model_dump"):
                    doc_meta_list.append(af.model_dump())

        new_msg = {
            "id": msg_id,
            "role": role,
            "content": content,
            "timestamp": now_iso,
            "sources": sources or [],
            "attached_files": doc_meta_list,
            "status": status
        }

        c.setdefault("messages", []).append(new_msg)

        # Auto-generate meaningful conversation title from first user query
        if role == "user" and (c.get("title") in ("New Chat", None, "") or len(c["messages"]) <= 1):
            clean_q = content.strip().replace("\n", " ")
            if len(clean_q) > 42:
                clean_q = clean_q[:42].rsplit(" ", 1)[0] + "..."
            c["title"] = clean_q

        c["updated_at"] = now_iso
        all_convs[conv_id] = c
        self._save_all(all_convs)

        return ConversationMessage(**new_msg)

    def delete_conversation(self, conv_id: str, user_id: str = "default_user") -> bool:
        """Deletes a conversation and purges its attached document data from data folder."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            return False

        c = all_convs[conv_id]
        conv_owner = c.get("user_id", settings.DEFAULT_USER_ID)
        if conv_owner != user_id and user_id not in ("user-admin-01", "sre_admin") and conv_owner != "default_user":
            raise UnauthorizedAccessError(f"You do not have permission to delete conversation '{conv_id}'.")

        # Collect all documents attached to this conversation
        attached_docs = c.get("documents", [])
        attached_doc_ids = set()
        for d in attached_docs:
            if isinstance(d, dict) and d.get("document_id"):
                attached_doc_ids.add(d["document_id"])
            elif isinstance(d, str):
                attached_doc_ids.add(d)

        for msg in c.get("messages", []):
            for af in msg.get("attached_files", []):
                if isinstance(af, dict) and af.get("document_id"):
                    attached_doc_ids.add(af["document_id"])

        del all_convs[conv_id]
        self._save_all(all_convs)
        logger.info(f"Deleted conversation '{conv_id}'.")

        # Check if attached documents are used in any remaining conversation for this user
        other_used_docs = set()
        for other_id, other_conv in all_convs.items():
            if other_conv.get("user_id") == conv_owner:
                for od in other_conv.get("documents", []):
                    if isinstance(od, dict) and od.get("document_id"):
                        other_used_docs.add(od["document_id"])
                    elif isinstance(od, str):
                        other_used_docs.add(od)
                for omsg in other_conv.get("messages", []):
                    for oaf in omsg.get("attached_files", []):
                        if isinstance(oaf, dict) and oaf.get("document_id"):
                            other_used_docs.add(oaf["document_id"])

        # Delete documents attached to this deleted chat from the data folder
        from app.services.document_service import document_service
        docs_to_delete = attached_doc_ids - other_used_docs
        for doc_id in docs_to_delete:
            try:
                document_service.delete_document(doc_id, user_id=user_id)
                logger.info(f"Cleaned up document {doc_id} associated with deleted conversation {conv_id} from data folder.")
            except Exception as de:
                logger.warning(f"Failed to delete attached document {doc_id} from data folder: {de}")

        return True

    def get_history(self, conv_id: str, user_id: str = "default_user", limit: int = 10) -> List[Dict[str, str]]:
        """Returns message history suitable for LLM prompt context."""
        all_convs = self._load_all()
        if conv_id not in all_convs:
            return []
        c = all_convs[conv_id]
        messages = c.get("messages", [])[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]

conversation_service = ConversationService()
