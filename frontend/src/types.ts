export interface HealthStatus {
  status: string;
  application: string;
  version: string;
}

export interface SourceReference {
  document_name: string;
  page_number: number;
  snippet: string;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: SourceReference[];
  status?: string;
}

export interface ChatRequestPayload {
  message: string;
  conversation_id?: string | null;
}

export interface ChatResponsePayload {
  conversation_id: string;
  message: string;
  answer?: string | null;
  sources: any[];
  status: string;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface DocumentChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  chunk_index: number;
  content: string;
  char_count: number;
  extraction_timestamp: string;
}

export interface DocumentProcessingStatusResponse {
  document_id: string;
  filename: string;
  status: 'uploaded' | 'processing' | 'processed' | 'failed';
  total_pages?: number | null;
  extracted_pages?: number | null;
  empty_pages?: number | null;
  failed_pages?: number | null;
  total_chunks?: number | null;
  total_characters?: number | null;
  processed_at?: string | null;
  error_message?: string | null;
}

export interface DocumentProcessingResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
  total_pages: number;
  extracted_pages: number;
  empty_pages: number;
  failed_pages: number;
  total_chunks: number;
  total_characters: number;
  chunks?: DocumentChunk[];
}

export interface DocumentMetadata {
  id: string;
  document_id: string;
  filename: string;
  size_bytes: number;
  content_type?: string;
  status: string;
  uploaded_at: string;
  filepath?: string;
  pages: number;
  chunks: number;
  error_message?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface RunbookItem {
  id: string;
  title: string;
  category: string;
  severity: string;
  summary: string;
  page_range: string;
  recommended_commands: string[];
}

export interface IncidentRecord {
  id: string;
  incident_number: string;
  title: string;
  severity: string;
  status: string;
  service: string;
  mttr_minutes: number;
  sla_breached: boolean;
  service_credit_tier: string;
  resolved_at: string;
  summary: string;
  runbook_ref: string;
  page: number;
}

export interface SettingsPayload {
  model_name: string;
  api_key?: string;
  temperature: number;
  top_k_chunks: number;
  response_style: string;
}
