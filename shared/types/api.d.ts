export interface ChatRequest {
  message: string;
  persona?: 'neutral' | 'yazan';
  language?: 'msa' | 'jordanian';
  household_id?: string;
  thread_id?: string | null;
  browser_id?: string;
}

export interface ChatResponse {
  reply: string;
  needs_human: boolean;
  safety_reasons: string[];
  context: string[];
  persona: 'neutral' | 'yazan';
  thread_id: string;
}

export interface ChatThreadSummary {
  thread_id: string;
  title: string;
  persona: string;
  lang: string;
  last_message_at: string;
}

export interface ChatHistoryResponse {
  thread_id: string;
  turns: Array<{ role: 'user' | 'assistant'; content: string }>;
}

export interface TipsResponse {
  age_range: string;
  tips: string[];
}

export interface ProfileCreatePayload {
  household_name: string;
  country: string;
  language_preference: string;
  parent_email: string;
  parent_password: string;
  children: Array<{
    name: string;
    age: number;
    favorite_topics?: string;
  }>;
}

export interface ProfileResponse {
  household_id: string;
  admin_token?: string;
}

export interface UploadResponse {
  document_id: string;
  stored_chunks: number;
}

export interface AdminDocument {
  document_id: string;
  file_name: string;
  topic: string;
  age_range: string;
  tone: string;
  country: string;
  language: string;
  chunk_count: number;
  s3_uploaded: boolean;
  updated_at: string;
}
