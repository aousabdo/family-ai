'use client';

import { useEffect, useState } from 'react';

import { deleteDocument, fetchAdminDocuments, uploadDocument } from '@/lib/api';
import type { AdminDocument } from '@/lib/types';

export default function AdminUploadPage() {
  const [token, setToken] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [topic, setTopic] = useState('general');
  const [ageRange, setAgeRange] = useState('all');
  const [tone, setTone] = useState('supportive');
  const [country, setCountry] = useState('jo');
  const [language, setLanguage] = useState('ar');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [documents, setDocuments] = useState<AdminDocument[]>([]);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [refreshFlag, setRefreshFlag] = useState(0);

  useEffect(() => {
    if (!token) {
      setDocuments([]);
      setDocsError(null);
      return;
    }
    setIsLoadingDocs(true);
    fetchAdminDocuments(token)
      .then((data) => {
        setDocuments(data);
        setDocsError(null);
      })
      .catch((err) => {
        setDocsError(err instanceof Error ? err.message : 'تعذر تحميل المكتبة');
      })
      .finally(() => setIsLoadingDocs(false));
  }, [token, refreshFlag]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('يرجى اختيار ملف');
      return;
    }
    setIsUploading(true);
    setError(null);
    setStatus(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('topic', topic);
      formData.append('age_range', ageRange);
      formData.append('tone', tone);
      formData.append('country', country);
      formData.append('language', language);
      const response = await uploadDocument(formData, token);
      setStatus(`تم رفع الوثيقة بنجاح (عدد المقاطع المخزنة: ${response.stored_chunks})`);
      setRefreshFlag((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'فشل الرفع');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!token) {
      setDocsError('الرجاء إدخال رمز الإدارة أولاً');
      return;
    }
    try {
      await deleteDocument(documentId, token);
      setRefreshFlag((value) => value + 1);
    } catch (err) {
      setDocsError(err instanceof Error ? err.message : 'تعذر حذف الوثيقة');
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('ar-JO', { dateStyle: 'short', timeStyle: 'short' });
    } catch (error) {
      return iso;
    }
  };

  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      <div style={{ background: '#fee2e2', borderRadius: '12px', padding: '1rem', color: '#991b1b' }}>
        للتذكير: رفع المحتوى متاح فقط للمشرفين المعتمدين. تُستخدم الملفات بتنسيق Markdown أو نص.
      </div>
      <form onSubmit={handleSubmit} style={{ background: '#ffffff', borderRadius: '16px', padding: '2rem', display: 'grid', gap: '1rem' }}>
        <label style={{ display: 'grid', gap: '0.5rem' }}>
          رمز الإدارة (JWT)
          <input
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder="Bearer token"
            required
            style={{ padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
          />
        </label>
        <label style={{ display: 'grid', gap: '0.5rem' }}>
          اختر ملفاً (.md أو .txt)
          <input type="file" accept=".md,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
        </label>
        <div style={{ display: 'grid', gap: '0.75rem', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))' }}>
          <label style={{ display: 'grid', gap: '0.5rem' }}>
          التصنيف الرئيسي
          <input value={topic} onChange={(event) => setTopic(event.target.value)} style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }} />
        </label>
        <label style={{ display: 'grid', gap: '0.5rem' }}>
          الفئة العمرية
            <input value={ageRange} onChange={(event) => setAgeRange(event.target.value)} style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }} />
          </label>
          <label style={{ display: 'grid', gap: '0.5rem' }}>
            النبرة
            <input value={tone} onChange={(event) => setTone(event.target.value)} style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }} />
          </label>
          <label style={{ display: 'grid', gap: '0.5rem' }}>
            البلد المستهدف
            <input value={country} onChange={(event) => setCountry(event.target.value)} style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }} />
          </label>
          <label style={{ display: 'grid', gap: '0.5rem' }}>
            اللغة
            <select value={language} onChange={(event) => setLanguage(event.target.value)} style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }}>
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        {status && <div style={{ color: '#047857' }}>{status}</div>}
        {error && <div style={{ color: '#b91c1c' }}>{error}</div>}
        <button
          type="submit"
          disabled={isUploading}
          style={{ padding: '0.9rem 1.4rem', borderRadius: '999px', border: 'none', background: isUploading ? '#9ca3af' : '#2563eb', color: '#ffffff', fontWeight: 600 }}
        >
          {isUploading ? '...جار الرفع' : 'رفع الوثيقة'}
        </button>
      </form>

      <section style={{ background: '#ffffff', borderRadius: '16px', padding: '1.5rem', display: 'grid', gap: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>مكتبة المستندات</h2>
        {!token && <p style={{ color: '#6b7280' }}>ادخل رمز الإدارة للاطلاع على المستندات المرفوعة.</p>}
        {docsError && <div style={{ color: '#b91c1c' }}>{docsError}</div>}
        {isLoadingDocs && <div>...جاري التحميل</div>}
        {!isLoadingDocs && token && documents.length === 0 && <div>لا توجد مستندات مرفوعة بعد.</div>}
        {!isLoadingDocs && documents.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '640px' }}>
              <thead>
                <tr style={{ background: '#f8fafc', textAlign: 'left' }}>
                  <th style={{ padding: '0.75rem' }}>الملف</th>
                  <th style={{ padding: '0.75rem' }}>الموضوع</th>
                  <th style={{ padding: '0.75rem' }}>الفئة العمرية</th>
                  <th style={{ padding: '0.75rem' }}>النبرة</th>
                  <th style={{ padding: '0.75rem' }}>اللغة</th>
                  <th style={{ padding: '0.75rem' }}>عدد المقاطع</th>
                  <th style={{ padding: '0.75rem' }}>آخر تحديث</th>
                  <th style={{ padding: '0.75rem' }}>إجراءات</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.document_id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '0.75rem' }}>{doc.file_name}</td>
                    <td style={{ padding: '0.75rem' }}>{doc.topic}</td>
                    <td style={{ padding: '0.75rem' }}>{doc.age_range}</td>
                    <td style={{ padding: '0.75rem' }}>{doc.tone}</td>
                    <td style={{ padding: '0.75rem' }}>{doc.language.toUpperCase()}</td>
                    <td style={{ padding: '0.75rem' }}>{doc.chunk_count}</td>
                    <td style={{ padding: '0.75rem' }}>{formatDate(doc.updated_at)}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <button
                        type="button"
                        onClick={() => handleDelete(doc.document_id)}
                        style={{ border: 'none', background: '#fee2e2', color: '#b91c1c', padding: '0.4rem 0.75rem', borderRadius: '8px' }}
                      >
                        حذف
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
