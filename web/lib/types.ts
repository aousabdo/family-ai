export type PersonaOption = 'neutral' | 'yazan';
export type LanguageOption = 'msa' | 'jordanian';

export interface ChatRequestBody {
  message: string;
  persona: PersonaOption;
  language: LanguageOption;
  household_id?: string;
  thread_id: string;
}

export interface ChatResponseBody {
  reply: string;
  needs_human: boolean;
  safety_reasons: string[];
  context: string[];
  persona: PersonaOption;
}

export interface TipResponse {
  age_range: string;
  tips: string[];
}

export interface ProfilePayload {
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
