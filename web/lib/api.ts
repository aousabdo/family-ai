import { AdminDocument, ChatRequestBody, ChatResponseBody, ProfilePayload, TipResponse } from './types';

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

export async function sendChat(body: ChatRequestBody): Promise<ChatResponseBody> {
  const res = await fetch(buildUrl('/chat'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return handleResponse<ChatResponseBody>(res);
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
