'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { claimThreads, createThread, fetchHistory, fetchThreads, loginHousehold, sendChat } from '@/lib/api';
import type { ChatResponseBody, ChatThreadSummary, LanguageOption, PersonaOption } from '@/lib/types';

import styles from './Chat.module.css';

const BROWSER_ID_KEY = 'family-ai-browser-id';
const TOKEN_KEY = 'family-ai-token';
const ACTIVE_THREAD_KEY = 'family-ai-active-thread';

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

function generateId() {
  if (typeof window !== 'undefined' && typeof window.crypto?.randomUUID === 'function') {
    return window.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function Chat() {
  const [persona, setPersona] = useState<PersonaOption>('neutral');
  const [language, setLanguage] = useState<LanguageOption>('msa');
  const [householdId, setHouseholdId] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [browserId, setBrowserId] = useState('');
  const [token, setToken] = useState<string | null>(null);
  const [threads, setThreads] = useState<ChatThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [isLoadingThreads, setIsLoadingThreads] = useState(false);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [messagesError, setMessagesError] = useState<string | null>(null);

  const [isLoginModalOpen, setLoginModalOpen] = useState(false);
  const [loginHouseholdId, setLoginHouseholdId] = useState('');
  const [loginSecret, setLoginSecret] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);

  const skipHistoryFetchRef = useRef(false);

  const disclaimer = useMemo(
    () =>
      persona === 'yazan'
        ? 'يزن صديقك الهادئ: إذا شعرت أن الوضع يحتاج مختصاً بشرياً فسيذكرك فوراً.'
        : 'المدرب المحايد يقدم إرشاداً عملياً ويحيل المواضيع الحساسة لخبير بشري.',
    [persona]
  );

  const setActiveThreadPersistent = useCallback((threadId: string | null) => {
    setActiveThreadId(threadId);
    if (typeof window === 'undefined') {
      return;
    }
    if (threadId) {
      window.sessionStorage.setItem(ACTIVE_THREAD_KEY, threadId);
    } else {
      window.sessionStorage.removeItem(ACTIVE_THREAD_KEY);
    }
  }, []);

  const syncThreadMetadata = useCallback(
    (threadId: string, source?: ChatThreadSummary[]) => {
      const list = source ?? threads;
      const found = list.find((item) => item.thread_id === threadId);
      if (found) {
        setPersona(found.persona === 'yazan' ? 'yazan' : 'neutral');
        setLanguage(found.lang === 'jordanian' ? 'jordanian' : 'msa');
      }
    },
    [threads]
  );

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    let id = window.localStorage.getItem(BROWSER_ID_KEY);
    if (!id) {
      id = generateId();
      window.localStorage.setItem(BROWSER_ID_KEY, id);
    }
    setBrowserId(id);

    const storedToken = window.localStorage.getItem(TOKEN_KEY);
    if (storedToken) {
      setToken(storedToken);
    }

    const storedThread = window.sessionStorage.getItem(ACTIVE_THREAD_KEY);
    if (storedThread) {
      setActiveThreadId(storedThread);
    }
  }, []);

  const loadThreads = useCallback(async () => {
    if (!browserId && !token) {
      return;
    }
    setThreadsError(null);
    setIsLoadingThreads(true);
    try {
      const data = await fetchThreads({ token, browserId });
      setThreads(data.threads);
      setThreadsError(null);

      if (data.threads.length === 0) {
        setActiveThreadPersistent(null);
        setMessages([]);
        return;
      }

      let targetId = activeThreadId;
      if (!targetId || !data.threads.some((thread) => thread.thread_id === targetId)) {
        targetId = data.threads[0].thread_id;
      }
      if (targetId) {
        syncThreadMetadata(targetId, data.threads);
        if (targetId !== activeThreadId) {
          setActiveThreadPersistent(targetId);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر تحميل المحادثات';
      setThreadsError(message);
    } finally {
      setIsLoadingThreads(false);
    }
  }, [activeThreadId, browserId, syncThreadMetadata, token, setActiveThreadPersistent]);

  const handleRetryThreads = useCallback(() => {
    void loadThreads();
  }, [loadThreads]);

  useEffect(() => {
    if (!threadsError) return;
    const timer = setTimeout(() => setThreadsError(null), 5000);
    return () => clearTimeout(timer);
  }, [threadsError]);

  const loadMessages = useCallback(
    async (threadId: string) => {
      setMessagesError(null);
      setIsLoadingMessages(true);
      try {
        const data = await fetchHistory(threadId, { token, browserId });
        const nextMessages: Message[] = data.turns.map((turn) => ({
          role: turn.role === 'assistant' ? 'assistant' : 'user',
          text: turn.content,
        }));
        setMessages(nextMessages);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'تعذر تحميل الرسائل';
        setMessagesError(message);
      } finally {
        setIsLoadingMessages(false);
      }
    },
    [browserId, token]
  );

  useEffect(() => {
    if (!browserId && !token) {
      return;
    }
    void loadThreads();
  }, [browserId, token, loadThreads]);

  useEffect(() => {
    if (!activeThreadId) {
      setMessages([]);
      return;
    }
    if (skipHistoryFetchRef.current) {
      skipHistoryFetchRef.current = false;
      return;
    }
    void loadMessages(activeThreadId);
  }, [activeThreadId, loadMessages]);

  const handleSelectThread = (threadId: string) => {
    syncThreadMetadata(threadId);
    setActiveThreadPersistent(threadId);
  };

  const handleStartNewThread = async () => {
    let sessionBrowserId = browserId;
    if (!sessionBrowserId) {
      sessionBrowserId = generateId();
      setBrowserId(sessionBrowserId);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(BROWSER_ID_KEY, sessionBrowserId);
      }
    }
    try {
      setError(null);
      const { thread_id } = await createThread(persona, language, { token, browserId: sessionBrowserId });
      setMessages([]);
      setActiveThreadPersistent(thread_id);
      await loadThreads();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر إنشاء محادثة جديدة';
      setError(message);
    }
  };

  const handleLoginSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!browserId) {
      setAuthError('لم يتم التعرف على المتصفح، أعد المحاولة.');
      return;
    }
    if (!loginHouseholdId.trim() || !loginSecret.trim()) {
      setAuthError('يرجى إدخال رمز العائلة والسر.');
      return;
    }
    setAuthError(null);
    try {
      const { access_token } = await loginHousehold(loginHouseholdId.trim(), loginSecret.trim());
      setToken(access_token);
      window.localStorage.setItem(TOKEN_KEY, access_token);
      await claimThreads(browserId, { token: access_token, browserId });
      setLoginModalOpen(false);
      setLoginSecret('');
      await loadThreads();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'فشل تسجيل الدخول';
      setAuthError(message);
    }
  };

  const handleLogout = async () => {
    setToken(null);
    window.localStorage.removeItem(TOKEN_KEY);
    await loadThreads();
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim()) return;

    setError(null);
    setIsLoading(true);

    let sessionBrowserId = browserId;
    if (!sessionBrowserId) {
      sessionBrowserId = generateId();
      setBrowserId(sessionBrowserId);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(BROWSER_ID_KEY, sessionBrowserId);
      }
    }

    const userMessage: Message = { role: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      const response = await sendChat(
        {
          message: userMessage.text,
          persona,
          language,
          household_id: householdId || undefined,
          thread_id: activeThreadId || undefined,
          browser_id: sessionBrowserId,
        },
        { token, browserId: sessionBrowserId }
      );

      const assistantMessage: Message = {
        role: 'assistant',
        text: response.reply,
        context: response.context,
        needsHuman: response.needs_human,
      };

      skipHistoryFetchRef.current = true;
      setMessages((prev) => [...prev, assistantMessage]);
      setActiveThreadPersistent(response.thread_id);
      await loadThreads();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر إرسال الرسالة';
      setError(message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const openLoginModal = () => {
    setLoginModalOpen(true);
    setAuthError(null);
  };

  const closeLoginModal = () => {
    setLoginModalOpen(false);
    setAuthError(null);
  };

  const isAuthenticated = Boolean(token);

  return (
    <section className={styles.container}>
      <aside className={styles.sidebar}>
        <div className={styles.threadSection}>
          <div className={styles.threadHeader}>
            <h3 className={styles.sectionTitle}>محادثاتي</h3>
            <div className={styles.threadActions}>
              <button type="button" className={styles.saveButton} onClick={openLoginModal}>
                احفظ محادثاتي
              </button>
              <button type="button" className={styles.newThreadButton} onClick={handleStartNewThread}>
                محادثة جديدة
              </button>
            </div>
          </div>
          {threadsError && (
            <div className={styles.errorBanner}>
              <span>{threadsError}</span>
              <button type="button" className={styles.retryButton} onClick={handleRetryThreads}>
                إعادة المحاولة
              </button>
            </div>
          )}
          <div className={styles.threadList}>
            {isLoadingThreads ? (
              <div className={styles.threadPlaceholder}>... جار تحميل المحادثات</div>
            ) : threads.length === 0 ? (
              <div className={styles.threadPlaceholder}>لا توجد محادثات محفوظة بعد.</div>
            ) : (
              threads.map((thread) => {
                const isActive = thread.thread_id === activeThreadId;
                return (
                  <button
                    key={thread.thread_id}
                    type="button"
                    className={`${styles.threadButton} ${isActive ? styles.threadButtonActive : ''}`.trim()}
                    onClick={() => handleSelectThread(thread.thread_id)}
                  >
                    <span className={styles.threadTitle}>{thread.title}</span>
                    <span className={styles.threadMeta}>
                      {thread.lang === 'jordanian' ? 'اللهجة الأردنية' : 'الفصحى'} ·{' '}
                      {thread.persona === 'yazan' ? 'يزن' : 'المدرب المحايد'}
                    </span>
                  </button>
                );
              })
            )}
          </div>
          {isAuthenticated && (
            <button type="button" className={styles.logoutButton} onClick={handleLogout}>
              تسجيل الخروج من الأسرة
            </button>
          )}
        </div>
      </aside>

      <div className={styles.chatStack}>
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
          {isLoadingMessages ? (
            <div className={styles.messagesEmpty}>... جار تحميل الرسائل</div>
          ) : messages.length === 0 ? (
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
                  {message.needsHuman && (
                    <div className={styles.needsHuman}>تم اكتشاف موضوع حساس. الرجاء التواصل مع مختص موثوق.</div>
                  )}
                </div>
              );
            })
          )}
          {messagesError && <div className={styles.error}>{messagesError}</div>}
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
      </div>

      {isLoginModalOpen && (
        <div className={styles.modalOverlay} role="dialog" aria-modal="true">
          <div className={styles.modalContent}>
            <div className={styles.modalHeader}>
              <h2>تسجيل دخول الأسرة</h2>
              <button type="button" className={styles.closeButton} onClick={closeLoginModal}>
                ×
              </button>
            </div>
            <form onSubmit={handleLoginSubmit} className={styles.loginForm}>
              <label className={styles.label}>
                رمز العائلة
                <input
                  value={loginHouseholdId}
                  onChange={(event) => setLoginHouseholdId(event.target.value)}
                  className={styles.input}
                  placeholder="household-123"
                  autoComplete="username"
                  dir="auto"
                />
              </label>
              <label className={styles.label}>
                السر الخاص
                <input
                  value={loginSecret}
                  onChange={(event) => setLoginSecret(event.target.value)}
                  className={styles.input}
                  placeholder="••••••"
                  type="password"
                  autoComplete="current-password"
                />
              </label>
              {authError && <div className={styles.error}>{authError}</div>}
              <button type="submit" className={styles.modalSubmitButton}>
                تسجيل الدخول
              </button>
            </form>
            {isAuthenticated && (
              <button type="button" className={styles.modalSecondaryButton} onClick={handleLogout}>
                تسجيل الخروج من الأسرة
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
