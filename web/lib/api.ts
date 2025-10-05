import {
  AdminDocument,
  ChatHistoryResponse,
  ChatRequestBody,
  ChatResponseBody,
  ChatThreadSummary,
  ProfilePayload,
  TipResponse,
} from './types';

const configuredBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, '') ?? '';

function buildUrl(path: string) {
  if (configuredBase) {
    return `${configuredBase}${path}`;
  }
  return `/api${path}`;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const contentType = res.headers.get('content-type') ?? '';
    try {
      if (contentType.includes('application/json')) {
        const payload = (await res.json()) as { detail?: string; message?: string };
        const message = payload.detail || payload.message;
        if (message) {
          throw new Error(message);
        }
      } else {
        const text = await res.text();
        if (text && !text.toLowerCase().includes('<html')) {
          throw new Error(text);
        }
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
    }
    throw new Error(`Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

interface AuthHeaders {
  token?: string | null;
  browserId?: string | null;
}

function buildHeaders(options: AuthHeaders = {}) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  if (options.browserId) {
    headers['x-browser-id'] = options.browserId;
  }
  return headers;
}

export async function sendChat(body: ChatRequestBody, options: AuthHeaders = {}): Promise<ChatResponseBody> {
  const res = await fetch(buildUrl('/chat'), {
    method: 'POST',
    headers: buildHeaders(options),
    body: JSON.stringify(body),
  });
  return handleResponse<ChatResponseBody>(res);
}

export async function fetchThreads(options: AuthHeaders = {}): Promise<{ threads: ChatThreadSummary[] }> {
  const res = await fetch(buildUrl('/chat/threads'), {
    headers: buildHeaders(options),
  });
  return handleResponse<{ threads: ChatThreadSummary[] }>(res);
}

export async function fetchHistory(threadId: string, options: AuthHeaders = {}): Promise<ChatHistoryResponse> {
  const search = new URLSearchParams({ thread_id: threadId });
  const res = await fetch(buildUrl(`/chat/history?${search.toString()}`), {
    headers: buildHeaders(options),
  });
  return handleResponse<ChatHistoryResponse>(res);
}

export async function createThread(
  persona: string | undefined,
  language: string | undefined,
  options: AuthHeaders = {}
): Promise<{ thread_id: string }> {
  const res = await fetch(buildUrl('/chat/new'), {
    method: 'POST',
    headers: buildHeaders(options),
    body: JSON.stringify({ persona, language }),
  });
  return handleResponse<{ thread_id: string }>(res);
}

export async function claimThreads(browserId: string, options: AuthHeaders = {}) {
  const res = await fetch(buildUrl('/chat/claim'), {
    method: 'POST',
    headers: buildHeaders(options),
    body: JSON.stringify({ browser_id: browserId }),
  });
  return handleResponse<{ moved: number }>(res);
}

export async function loginHousehold(household_id: string, secret: string): Promise<{ access_token: string }> {
  const res = await fetch(buildUrl('/auth/household/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ household_id, secret }),
  });
  return handleResponse<{ access_token: string }>(res);
}

export async function fetchTips(ageRange: string): Promise<TipResponse> {
  const search = new URLSearchParams({ age_range: ageRange });
  const url = buildUrl(`/tips?${search.toString()}`);
  return handleResponse<TipResponse>(await fetch(url));
}

export async function createProfile(payload: ProfilePayload) {
  const res = await fetch(buildUrl('/profile'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<{ household_id: string; admin_token: string }>(res);
}

export async function uploadDocument(formData: FormData, token: string) {
  const res = await fetch(buildUrl('/admin/upload'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  return handleResponse<{ document_id: string; stored_chunks: number }>(res);
}

export async function fetchAdminDocuments(token: string): Promise<AdminDocument[]> {
  const res = await fetch(buildUrl('/admin/documents'), {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return handleResponse<AdminDocument[]>(res);
}

export async function deleteDocument(documentId: string, token: string) {
  const res = await fetch(buildUrl(`/admin/documents/${documentId}`), {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok && res.status !== 204) {
    const text = await res.text();
    throw new Error(text || `Failed to delete document (${res.status})`);
  }
}
