import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from app.schemas import DocumentMetadata, ConversationDetail, ConversationSummary, ChatMessage, SettingsPayload

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
DB_FILE = os.path.join(DATA_DIR, "state.json")

os.makedirs(DOCUMENTS_DIR, exist_ok=True)

class Storage:
    def __init__(self):
        self.state_file = DB_FILE
        self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents: Dict[str, dict] = data.get("documents", {})
                    self.conversations: Dict[str, dict] = data.get("conversations", {})
                    self.settings: dict = data.get("settings", {
                        "model_name": "gemini-2.0-flash",
                        "api_key": "",
                        "temperature": 0.2,
                        "top_k_chunks": 4,
                        "response_style": "enterprise_sre"
                    })
                    return
            except Exception as e:
                print(f"Error loading state: {e}")
        self.documents = {}
        self.conversations = {}
        self.settings = {
            "model_name": "gemini-2.0-flash",
            "api_key": "",
            "temperature": 0.2,
            "top_k_chunks": 4,
            "response_style": "enterprise_sre"
        }
        self._save()

    def _save(self):
        data = {
            "documents": self.documents,
            "conversations": self.conversations,
            "settings": self.settings
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Document management
    def save_document(self, doc: DocumentMetadata):
        self.documents[doc.id] = doc.model_dump()
        self._save()

    def get_document(self, doc_id: str) -> Optional[DocumentMetadata]:
        d = self.documents.get(doc_id)
        if d:
            return DocumentMetadata(**d)
        return None

    def list_documents(self) -> List[DocumentMetadata]:
        return [DocumentMetadata(**d) for d in self.documents.values()]

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self.documents:
            filepath = self.documents[doc_id].get("filepath")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            del self.documents[doc_id]
            self._save()
            return True
        return False

    # Conversation management
    def save_conversation(self, conv: ConversationDetail):
        self.conversations[conv.id] = conv.model_dump()
        self._save()

    def get_conversation(self, conv_id: str) -> Optional[ConversationDetail]:
        c = self.conversations.get(conv_id)
        if c:
            return ConversationDetail(**c)
        return None

    def list_conversations(self) -> List[ConversationSummary]:
        results = []
        for c in self.conversations.values():
            results.append(ConversationSummary(
                id=c["id"],
                title=c["title"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                message_count=len(c.get("messages", []))
            ))
        results.sort(key=lambda x: x.updated_at, reverse=True)
        return results

    def delete_conversation(self, conv_id: str) -> bool:
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            self._save()
            return True
        return False

    def get_settings(self) -> SettingsPayload:
        return SettingsPayload(**self.settings)

    def save_settings(self, settings: SettingsPayload):
        self.settings = settings.model_dump()
        self._save()

storage = Storage()
