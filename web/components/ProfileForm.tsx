'use client';

import { useState } from 'react';

import { createProfile } from '@/lib/api';
import type { ProfilePayload } from '@/lib/types';

export default function ProfileForm() {
  const [payload, setPayload] = useState<ProfilePayload>({
    household_name: '',
    country: 'JO',
    language_preference: 'ar',
    parent_email: '',
    parent_password: '',
    children: [],
  });
  const [childDraft, setChildDraft] = useState({ name: '', age: 6, favorite_topics: '' });
  const [result, setResult] = useState<{ household_id: string; admin_token: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const addChild = () => {
    if (!childDraft.name.trim()) return;
    setPayload((current) => ({
      ...current,
      children: [
        ...current.children,
        { name: childDraft.name, age: Number(childDraft.age), favorite_topics: childDraft.favorite_topics || undefined },
      ],
    }));
    setChildDraft({ name: '', age: 6, favorite_topics: '' });
  };

  const removeChild = (index: number) => {
    setPayload((current) => ({
      ...current,
      children: current.children.filter((_, idx) => idx !== index),
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const response = await createProfile(payload);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'تعذر إنشاء الحساب');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '1.25rem', background: '#ffffff', padding: '2rem', borderRadius: '16px', boxShadow: '0 8px 20px rgba(15,23,42,0.08)' }}>
      <div>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>اسم العائلة</label>
        <input
          value={payload.household_name}
          onChange={(event) => setPayload((current) => ({ ...current, household_name: event.target.value }))}
          required
          style={{ width: '100%', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
        />
      </div>
      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>الدولة</label>
          <input
            value={payload.country}
            onChange={(event) => setPayload((current) => ({ ...current, country: event.target.value }))}
            style={{ width: '100%', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>تفضيل اللغة</label>
          <select
            value={payload.language_preference}
            onChange={(event) => setPayload((current) => ({ ...current, language_preference: event.target.value }))}
            style={{ width: '100%', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
          >
            <option value="ar">العربية</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
      <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>البريد الإلكتروني لولي الأمر</label>
          <input
            type="email"
            value={payload.parent_email}
            onChange={(event) => setPayload((current) => ({ ...current, parent_email: event.target.value }))}
            required
            style={{ width: '100%', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '0.5rem' }}>كلمة مرور أولية</label>
          <input
            type="password"
            value={payload.parent_password}
            onChange={(event) => setPayload((current) => ({ ...current, parent_password: event.target.value }))}
            required
            style={{ width: '100%', padding: '0.75rem 1rem', borderRadius: '12px', border: '1px solid #d1d5db' }}
          />
        </div>
      </div>

      <fieldset style={{ border: '1px dashed #cbd5f5', borderRadius: '12px', padding: '1rem 1.5rem' }}>
        <legend style={{ padding: '0 0.5rem' }}>الأطفال</legend>
        <div style={{ display: 'grid', gap: '0.75rem', marginBottom: '1rem', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))' }}>
          <input
            placeholder="الاسم"
            value={childDraft.name}
            onChange={(event) => setChildDraft((current) => ({ ...current, name: event.target.value }))}
            style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }}
          />
          <input
            type="number"
            placeholder="العمر"
            value={childDraft.age}
            onChange={(event) => setChildDraft((current) => ({ ...current, age: Number(event.target.value) }))}
            min={0}
            style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }}
          />
          <input
            placeholder="اهتمامات"
            value={childDraft.favorite_topics}
            onChange={(event) => setChildDraft((current) => ({ ...current, favorite_topics: event.target.value }))}
            style={{ padding: '0.6rem 0.9rem', borderRadius: '10px', border: '1px solid #d1d5db' }}
          />
          <button type="button" onClick={addChild} style={{ borderRadius: '10px', border: 'none', background: '#0ea5e9', color: '#fff', fontWeight: 600 }}>
            إضافة طفل
          </button>
        </div>
        <ul style={{ listStyle: 'inside', padding: 0, margin: 0, display: 'grid', gap: '0.5rem' }}>
          {payload.children.map((child, index) => (
            <li key={`${child.name}-${index}`} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#f8fafc', borderRadius: '8px', padding: '0.5rem 0.75rem' }}>
              <span>
                {child.name} — {child.age} سنة {child.favorite_topics ? `| ${child.favorite_topics}` : ''}
              </span>
              <button type="button" onClick={() => removeChild(index)} style={{ border: 'none', background: 'transparent', color: '#ef4444', fontWeight: 600 }}>
                إزالة
              </button>
            </li>
          ))}
        </ul>
      </fieldset>

      {error && <span style={{ color: '#b91c1c' }}>{error}</span>}
      {result && (
        <div style={{ background: '#ecfdf5', borderRadius: '12px', padding: '1rem', color: '#047857', fontSize: '0.95rem' }}>
          <p style={{ margin: 0 }}>تم إنشاء الملف العائلي بنجاح.</p>
          <p style={{ margin: 0 }}>معرف العائلة: <strong>{result.household_id}</strong></p>
          <p style={{ margin: 0 }}>رمز الإدارة (JWT): <code>{result.admin_token}</code></p>
        </div>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        style={{ padding: '0.9rem 1.4rem', borderRadius: '999px', border: 'none', background: isSubmitting ? '#9ca3af' : '#16a34a', color: '#ffffff', fontWeight: 600 }}
      >
        {isSubmitting ? '...جاري الحفظ' : 'حفظ الملف العائلي'}
      </button>
    </form>
  );
}
