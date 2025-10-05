'use client';

import { useEffect, useMemo, useState } from 'react';

import { sendChat } from '@/lib/api';
import type { ChatResponseBody, LanguageOption, PersonaOption } from '@/lib/types';

import styles from './Chat.module.css';

const THREAD_KEY = 'family-ai-thread-id';

interface Message {
  role: 'user' | 'assistant';
  text: string;
  context?: string[];
  needsHuman?: boolean;
}

const personaLabels: Record<PersonaOption, string> = {
  neutral: 'المدرب المحايد',
  yazan: 'صوت يزن',
};

const languageLabels: Record<LanguageOption, string> = {
  msa: 'الفصحى',
  jordanian: 'اللهجة الأردنية',
};

const trailingNeedsHumanPattern = /(?:\n|\r\n)?(?:[-–—]{3,}\s*)?(?:\*{0,2}needs_human:\*{0,2}\s*(?:true|false))\s*$/i;

function stripNeedsHumanTag(text: string) {
  return text.replace(trailingNeedsHumanPattern, '').trimEnd();
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function applyInlineMarkdown(text: string) {
  let output = escapeHtml(text);
  output = output.replace(/`([^`]+)`/g, '<code>$1</code>');
  output = output.replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  output = output.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  output = output.replace(/\*(?!\*)([^*]+)\*/g, '<em>$1</em>');
  return output;
}

function markdownToHtml(markdown: string) {
  const lines = markdown.split(/\r?\n/);
  const html: string[] = [];
  let paragraphBuffer: string[] = [];
  let listOpen = false;

  const flushParagraph = () => {
    if (paragraphBuffer.length === 0) return;
    html.push(`<p>${applyInlineMarkdown(paragraphBuffer.join(' '))}</p>`);
    paragraphBuffer = [];
  };

  const closeList = () => {
    if (listOpen) {
      html.push('</ul>');
      listOpen = false;
    }
  };

  for (const line of lines) {
    const trimmed = line.trimEnd();
    if (!trimmed.trim()) {
      flushParagraph();
      closeList();
      continue;
    }

    if (/^[-–—]{3,}\s*$/.test(trimmed)) {
      flushParagraph();
      closeList();
      html.push('<hr />');
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      flushParagraph();
      closeList();
      const level = Math.min(headingMatch[1].length, 3);
      html.push(`<h${level}>${applyInlineMarkdown(headingMatch[2].trim())}</h${level}>`);
      continue;
    }

    const listMatch = trimmed.match(/^[-*+]\s+(.*)$/);
    if (listMatch) {
      flushParagraph();
      if (!listOpen) {
        html.push('<ul>');
        listOpen = true;
      }
      html.push(`<li>${applyInlineMarkdown(listMatch[1].trim())}</li>`);
      continue;
    }

    if (/^>\s?/.test(trimmed)) {
      flushParagraph();
      closeList();
      html.push(`<blockquote>${applyInlineMarkdown(trimmed.replace(/^>\s?/, '').trim())}</blockquote>`);
      continue;
    }

    closeList();
    paragraphBuffer.push(trimmed);
  }

  flushParagraph();
  closeList();

  if (html.length === 0) {
    return `<p>${applyInlineMarkdown(markdown)}</p>`;
  }

  return html.join('');
}

function MarkdownMessage({ text }: { text: string }) {
  const html = useMemo(() => markdownToHtml(stripNeedsHumanTag(text)), [text]);
  return <div className={styles.markdown} dir="auto" dangerouslySetInnerHTML={{ __html: html }} />;
}

export default function Chat() {
  const [persona, setPersona] = useState<PersonaOption>('neutral');
  const [language, setLanguage] = useState<LanguageOption>('msa');
  const [householdId, setHouseholdId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [threadId, setThreadId] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    try {
      const storage = window.sessionStorage;
      let existing = storage.getItem(THREAD_KEY);
      if (!existing) {
        existing = window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
        storage.setItem(THREAD_KEY, existing);
      }
      setThreadId(existing);
    } catch {
      const fallback = typeof window.crypto?.randomUUID === 'function' ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      setThreadId(fallback);
    }
  }, []);

  const disclaimer = useMemo(
    () =>
      persona === 'yazan'
        ? 'يزن صديقك الهادئ: إذا شعرت أن الوضع يحتاج مختصاً بشرياً فسيذكرك فوراً.'
        : 'المدرب المحايد يقدم إرشاداً عملياً ويحيل المواضيع الحساسة لخبير بشري.',
    [persona]
  );

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) return;
    let activeThreadId = threadId;
    if (!activeThreadId) {
      activeThreadId = window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      setThreadId(activeThreadId);
      try {
        if (typeof window !== 'undefined') {
          window.sessionStorage.setItem(THREAD_KEY, activeThreadId);
        }
      } catch {
        /* ignore persistence failure */
      }
    }

    setIsLoading(true);
    setError(null);

    const userMessage: Message = { role: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const response = await sendChat({
        message: userMessage.text,
        persona,
        language,
        household_id: householdId || undefined,
        thread_id: activeThreadId,
      });
      appendAssistant(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر إرسال الرسالة';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const appendAssistant = (payload: ChatResponseBody) => {
    const assistantMessage: Message = {
      role: 'assistant',
      text: payload.reply,
      context: payload.context,
      needsHuman: payload.needs_human,
    };
    setMessages((prev) => [...prev, assistantMessage]);
  };

  return (
    <section className={styles.container}>
      <article className={styles.configCard}>
        <div className={styles.selectorRow}>
          <div className={styles.selectorGroup}>
            <label className={styles.selectorLabel}>اختر الشخصية</label>
            <div className={styles.chipGroup}>
              {Object.entries(personaLabels).map(([key, label]) => {
                const className = `${styles.chip} ${persona === key ? styles.chipActive : ''}`.trim();
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setPersona(key as PersonaOption)}
                    className={className}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className={styles.selectorGroup}>
            <label className={styles.selectorLabel}>اختيار اللغة</label>
            <div className={styles.chipGroup}>
              {Object.entries(languageLabels).map(([key, label]) => {
                const className = `${styles.chip} ${language === key ? styles.chipActive : ''}`.trim();
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setLanguage(key as LanguageOption)}
                    className={className}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
          <div className={styles.selectorGroup}>
            <label className={styles.selectorLabel}>رمز العائلة (اختياري)</label>
            <input
              value={householdId}
              onChange={(event) => setHouseholdId(event.target.value)}
              placeholder="household-123"
              className={styles.householdInput}
              inputMode="text"
            />
          </div>
        </div>
        <p className={styles.disclaimer}>{disclaimer}</p>
      </article>

      <div className={styles.messagesCard} aria-live="polite">
        {messages.length === 0 ? (
          <div className={styles.messagesEmpty}>ابدأ الحوار بكتابة موقف ترغب بمناقشته.</div>
        ) : (
          messages.map((message, index) => {
            const baseClass = message.role === 'user' ? styles.messageUser : styles.messageAssistant;
            const className = `${styles.message} ${baseClass}`.trim();
            return (
              <div key={`${message.role}-${index}`} className={className}>
                {message.role === 'assistant' ? (
                  <MarkdownMessage text={message.text} />
                ) : (
                  <p className={styles.messageText} dir="auto">
                    {message.text}
                  </p>
                )}
                {message.role === 'assistant' && message.context && message.context.length > 0 && (
                  <details className={styles.context}>
                    <summary>السياق المستخدم</summary>
                    <ul>
                      {message.context.map((ctx) => (
                        <li key={ctx}>{ctx}</li>
                      ))}
                    </ul>
                  </details>
                )}
                {message.needsHuman && (
                  <div className={styles.needsHuman}>تم اكتشاف موضوع حساس. الرجاء التواصل مع مختص موثوق.</div>
                )}
              </div>
            );
          })
        )}
      </div>

      <form onSubmit={handleSubmit} className={styles.formCard}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="صف الموقف الذي ترغب بمناقشته..."
          rows={4}
          className={styles.textarea}
          dir="auto"
        />
        {error && <span className={styles.error}>{error}</span>}
        <div className={styles.actions}>
          <button type="submit" disabled={isLoading} className={styles.submitButton} aria-busy={isLoading}>
            {isLoading ? (
              <>
                <span className={styles.loadingDot} aria-hidden="true" />
                <span>جار معالجة الطلب...</span>
              </>
            ) : (
              'أرسل'
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
