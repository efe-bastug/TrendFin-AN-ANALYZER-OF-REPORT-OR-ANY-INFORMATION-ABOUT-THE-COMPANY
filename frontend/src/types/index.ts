export interface ApiResponse<T> {
  results?: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;
}

export interface PDFDocument {
  id: string;
  name: string;
  original_filename: string;
  size: number;
  uploaded_at: string;
  processed: boolean;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  total_pages?: number;
  file_url?: string;
  chunks_count?: number;
}

export interface DocumentChunk {
  id: string;
  document: string;
  document_name: string;
  chunk_index: number;
  content: string;
  page_start: number;
  page_end: number;
  token_count: number;
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages_count: number;
  last_message?: {
    content: string;
    role: string;
    created_at: string;
  };
}

export interface ChatMessage {
  id: string;
  session: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokens_used?: number;
  created_at: string;
  citations?: Citation[];
}

export interface Citation {
  id: string;
  document_id: string;
  document_name: string;
  page_start: number;
  page_end: number;
  content_preview: string;
  relevance_score: number;
}

export interface QuestionRequest {
  question: string;
  session_id?: string;
  document_ids?: string[];
  stream?: boolean;
}

export interface QuickAnswerRequest {
  question: string;
  document_ids?: string[];
}

export interface ChatResponse {
  session_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  citations: Citation[];
  has_context: boolean;
}

export interface QuickAnswerResponse {
  question: string;
  answer: string;
  has_context: boolean;
  citations: Citation[];
}

export interface UploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  document?: PDFDocument;
  error?: string;
}

export interface DocumentStats {
  total_documents: number;
  processed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_size_bytes: number;
  total_size_mb: number;
  total_chunks: number;
  total_pages: number;
}

export interface ChatStats {
  total_sessions: number;
  total_messages: number;
  active_sessions: number;
}

export interface StreamMessage {
  type: 'metadata' | 'content' | 'completion' | 'error';
  session_id?: string;
  user_message_id?: string;
  assistant_message_id?: string;
  has_context?: boolean;
  citations?: Citation[];
  content?: string;
  error?: string;
}

export interface UIState {
  sidebarOpen: boolean;
  darkMode: boolean;
  uploadModalOpen: boolean;
  selectedDocuments: string[];
}

export interface ApiError {
  message: string;
  details?: any;
  status?: number;
}

export interface UseApiOptions {
  enabled?: boolean;
  refetchInterval?: number;
  retry?: boolean | number;
}

export interface UseUploadOptions {
  onSuccess?: (document: PDFDocument) => void;
  onError?: (error: ApiError) => void;
  onProgress?: (progress: number) => void;
}

export interface PDFViewerProps {
  documentId: string;
  pageNumber?: number;
  highlightText?: string;
}

export interface ChatFormData {
  question: string;
  selectedDocuments: string[];
}

export interface UploadFormData {
  files: FileList;
  name?: string;
}