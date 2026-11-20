import {
  HealthStatus,
  ChatMessage,
  ChatResponsePayload,
  DocumentMetadata,
  DocumentUploadResponse,
  ConversationDetail,
  ConversationSummary,
  IncidentRecord,
  RunbookItem,
  SettingsPayload,
  SourceReference,
  UserProfile,
  AuthTokenResponse,
  AttachedDocument
} from './types';

// Centralized API configuration supporting environment variables
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

/**
 * Authentication Helpers
 */
export function getAuthToken(): string | null {
  return localStorage.getItem('inframind_token');
}

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('inframind_token', token);
  } else {
    localStorage.removeItem('inframind_token');
  }
}

export function logoutUser() {
  localStorage.removeItem('inframind_token');
  localStorage.removeItem('inframind_user');
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginUser(email: string, password: string): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error?.message || 'Login failed');
  }
  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  localStorage.setItem('inframind_user', JSON.stringify(data));
  return data;
}

export async function registerUser(username: string, email: string, password: string, fullName?: string): Promise<AuthTokenResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password, full_name: fullName })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error?.message || 'Registration failed');
  }
  const data: AuthTokenResponse = await res.json();
  setAuthToken(data.access_token);
  localStorage.setItem('inframind_user', JSON.stringify(data));
  return data;
}

export async function fetchCurrentUser(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    throw new Error('Unauthorized');
  }
  return res.json();
}

/**
 * Health Check API
 * Verifies backend connectivity and returns service status.
 */
export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Health check failed with HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Chat API
 * Sends user infrastructure message to POST /api/v1/chat
 */
export async function sendChatMessage(
  message: string,
  conversationId?: string | null,
  documentIds?: string[]
): Promise<{
  conversation_id: string;
  message: ChatMessage;
  sources: SourceReference[];
  attached_documents?: AttachedDocument[];
}> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
      document_ids: documentIds && documentIds.length > 0 ? documentIds : undefined
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || `Chat request failed with status ${res.status}`);
  }

  const data: any = await res.json();

  const responseContent = data.answer || data.message || 
    `> **[InfraMind Backend Response]**\n>\n> Inquiry received and processed.\n>\n> **Status:** \`${data.status}\`\n> **Conversation ID:** \`${data.conversation_id}\``;

  const assistantMessage: ChatMessage = {
    id: data.conversation_id + '-' + Date.now(),
    role: 'assistant',
    content: responseContent,
    timestamp: new Date().toISOString(),
    sources: data.sources || [],
    status: data.status
  };

  const attachedDocs: AttachedDocument[] = (data.attached_documents || []).map((d: any) => ({
    id: d.document_id,
    document_id: d.document_id,
    name: d.document_name,
    size_bytes: d.size_bytes,
    isUploading: false
  }));

  return {
    conversation_id: data.conversation_id,
    message: assistantMessage,
    sources: (data.sources as SourceReference[]) || [],
    attached_documents: attachedDocs
  };
}

/**
 * Trigger ChromaDB and BM25 indexing for a document
 */
export async function indexDocument(documentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/index`, {
    method: 'POST',
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || 'Failed to index document');
  }
  return res.json();
}

/**
 * Document Upload API
 * Sends PDF file to POST /api/v1/documents/upload
 */
export async function uploadDocument(file: File): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    headers: { ...getAuthHeaders() },
    body: formData
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || `Failed to upload document (HTTP ${res.status})`);
  }

  return res.json();
}

/**
 * Document Listing API
 * Retrieves all uploaded documents from GET /api/v1/documents
 */
export async function fetchDocuments(): Promise<DocumentMetadata[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || 'Failed to fetch documents');
  }
  const rawList = await res.json();
  // Map fields for UI compatibility
  return rawList.map((doc: any) => ({
    ...doc,
    id: doc.document_id,
    pages: doc.pages || 1,
    chunks: doc.chunks || 1
  }));
}

/**
 * Document Retrieval API
 * Retrieves a single document metadata from GET /api/v1/documents/{document_id}
 */
export async function fetchDocument(documentId: string): Promise<DocumentMetadata> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || 'Failed to fetch document');
  }
  const doc = await res.json();
  return {
    ...doc,
    id: doc.document_id,
    pages: doc.pages || 1,
    chunks: doc.chunks || 1
  };
}

/**
 * Document Deletion API
 * Deletes document from DELETE /api/v1/documents/{document_id}
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${documentId}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || 'Failed to delete document');
  }
}

/**
 * Phase 3: Process Document API
 * Triggers PDF page extraction, text cleaning, character chunking, and persistence.
 */
export async function processDocument(documentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/process`, {
    method: 'POST',
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || 'Failed to process document');
  }
  return res.json();
}

/**
 * Phase 3: Processing Status API
 * Retrieves document extraction and chunking statistics.
 */
export async function fetchProcessingStatus(documentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/processing-status`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || 'Failed to fetch processing status');
  }
  return res.json();
}

export interface DocumentStageInfo {
  document_id: string;
  stage: 'uploading' | 'extracting_text' | 'analyzing_pages' | 'chunking_document' | 'generating_embeddings' | 'indexing_document' | 'ready' | 'failed';
  progress: number;
  message: string;
  error?: string | null;
  updated_at?: string;
}

/**
 * Real-time granular processing stage API
 */
export async function fetchDocumentStage(documentId: string): Promise<DocumentStageInfo> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/stage`, {
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || 'Failed to fetch document stage');
  }
  return res.json();
}

/**
 * Phase 3: Document Chunks Retrieval API
 */
export async function fetchDocumentChunks(documentId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || 'Failed to fetch document chunks');
  }
  return res.json();
}

// Persistent Conversation Backend API
export async function fetchConversations(): Promise<ConversationSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/conversations`, {
      headers: { ...getAuthHeaders() }
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map((c: any) => ({
          ...c,
          documents: (c.documents || []).map((d: any) => ({
            id: d.document_id,
            document_id: d.document_id,
            name: d.document_name,
            size_bytes: d.size_bytes,
            isUploading: false
          }))
        }));
      }
    }
  } catch (err) {
    console.error('Failed to fetch backend conversations:', err);
  }

  return [];
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  try {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      headers: { ...getAuthHeaders() }
    });
    if (res.ok) {
      const c = await res.json();
      return {
        ...c,
        documents: (c.documents || []).map((d: any) => ({
          id: d.document_id,
          document_id: d.document_id,
          name: d.document_name,
          size_bytes: d.size_bytes,
          isUploading: false
        })),
        messages: (c.messages || []).map((m: any) => ({
          ...m,
          sources: m.sources || [],
          attachedFiles: (m.attached_files || []).map((d: any) => ({
            id: d.document_id,
            document_id: d.document_id,
            name: d.document_name,
            size_bytes: d.size_bytes,
            isUploading: false
          }))
        }))
      };
    }
  } catch (err) {
    console.error(`Failed to fetch backend conversation ${id}:`, err);
  }

  return {
    id,
    title: 'New Chat',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    documents: [],
    messages: []
  };
}

export async function createConversation(title?: string, documentIds?: string[]): Promise<ConversationDetail> {
  try {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ title: title || 'New Chat', document_ids: documentIds || [] })
    });
    if (res.ok) {
      const c = await res.json();
      return {
        ...c,
        documents: (c.documents || []).map((d: any) => ({
          id: d.document_id,
          document_id: d.document_id,
          name: d.document_name,
          size_bytes: d.size_bytes,
          isUploading: false
        })),
        messages: []
      };
    }
  } catch (err) {
    console.error('Failed to create backend conversation:', err);
  }

  const newId = 'conv-' + Date.now();
  return {
    id: newId,
    title: title || 'New Chat',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    documents: [],
    messages: []
  };
}

export async function deleteConversation(id: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE',
      headers: { ...getAuthHeaders() }
    });
  } catch (err) {
    console.error(`Failed to delete conversation ${id} on backend:`, err);
  }
}

export async function attachDocumentToConversation(conversationId: string, documentId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/documents/${documentId}`, {
    method: 'POST',
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.detail || 'Failed to attach document to conversation');
  }
  const c = await res.json();
  return {
    ...c,
    documents: (c.documents || []).map((d: any) => ({
      id: d.document_id,
      document_id: d.document_id,
      name: d.document_name,
      size_bytes: d.size_bytes,
      isUploading: false
    }))
  };
}

export async function detachDocumentFromConversation(conversationId: string, documentId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/documents/${documentId}`, {
    method: 'DELETE',
    headers: { ...getAuthHeaders() }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || err.detail || 'Failed to detach document from conversation');
  }
  const c = await res.json();
  return {
    ...c,
    documents: (c.documents || []).map((d: any) => ({
      id: d.document_id,
      document_id: d.document_id,
      name: d.document_name,
      size_bytes: d.size_bytes,
      isUploading: false
    }))
  };
}

export async function fetchDocumentPage(docId: string, pageNumber: number) {
  return {
    document_id: docId,
    document_name: "titancloud_sre_incident_runbook_50p.pdf",
    page_number: pageNumber,
    total_pages: 50,
    text: `Page ${pageNumber} content indexed. Phase 2 document management active.`
  };
}

export async function fetchRunbooks(): Promise<RunbookItem[]> {
  return [
    {
      id: "rb-k8s",
      title: "Kubernetes Cluster Outage & Control Plane Failures",
      category: "Kubernetes Infrastructure",
      severity: "SEV-1",
      summary: "etcd quorum loss, API server 504 timeouts, master node isolation, and emergency defragmentation.",
      page_range: "Pages 4–8",
      recommended_commands: ["etcdctl endpoint health", "kubectl get nodes -o wide"]
    },
    {
      id: "rb-db",
      title: "Database Replication Lag & Patroni HA Failover",
      category: "Relational Database",
      severity: "SEV-1",
      summary: "Aurora and PostgreSQL streaming replication lag, WAL replay backlog, and Patroni automated failover.",
      page_range: "Pages 9–14",
      recommended_commands: ["SELECT * FROM pg_stat_replication;"]
    },
    {
      id: "rb-gw",
      title: "API Gateway Failure & Envoy Circuit Breaking",
      category: "Traffic Ingress",
      severity: "SEV-1",
      summary: "Envoy proxy 502/504 mitigation, rate limit token bucket tuning, and DDoS edge shedding.",
      page_range: "Pages 15–20",
      recommended_commands: ["curl -s http://127.0.0.1:15000/stats"]
    },
    {
      id: "rb-cpu",
      title: "Critical CPU & Memory Exhaustion",
      category: "Compute & Host",
      severity: "SEV-2",
      summary: "Kernel CFS quota throttling, JVM heap sizing, Full GC stalls, and EBS volume IOPS exhaustion.",
      page_range: "Pages 21–25",
      recommended_commands: ["cat /sys/fs/cgroup/cpu/kubepods/pod*/cpu.stat"]
    }
  ];
}

export async function fetchIncidents(): Promise<IncidentRecord[]> {
  return [
    {
      id: "inc-2026-089",
      incident_number: "INC-2026-089",
      title: "US-East Primary Aurora PostgreSQL Read Replica Lag Spike",
      severity: "SEV-1",
      status: "Resolved",
      service: "Aurora Postgres / Billing DB",
      mttr_minutes: 24,
      sla_breached: false,
      service_credit_tier: "None (99.96% Monthly)",
      resolved_at: "2026-11-18T16:42:00Z",
      summary: "Analytical batch query held locks on invoices table, stalling WAL replay by 1.2GB. Terminated query and enlarged pool.",
      runbook_ref: "Database Replication Lag",
      page: 9
    }
  ];
}

export async function globalSearch(q: string) {
  return {
    query: q,
    conversations: [
      { id: "workspace-1", title: "Kubernetes Cluster Outage", type: "conversation", updated_at: new Date().toISOString() }
    ],
    runbooks: [
      { id: "rb-k8s", title: "Kubernetes Cluster Outage & Control Plane Failures", type: "runbook", category: "Kubernetes", page_range: "Pages 4–8" }
    ],
    documents: [
      { document_name: "titancloud_sre_incident_runbook_50p.pdf", page_number: 4, section: "2.0 Kubernetes Infrastructure", snippet: "kubectl commands fail with Error: connection refused or etcd cluster is unavailable...", type: "document_snippet" }
    ]
  };
}

export async function fetchSettings(): Promise<SettingsPayload> {
  return {
    model_name: "gemini-2.0-flash",
    api_key: "",
    temperature: 0.2,
    top_k_chunks: 4,
    response_style: "enterprise_sre"
  };
}

export async function saveSettings(payload: SettingsPayload): Promise<SettingsPayload> {
  return payload;
}
