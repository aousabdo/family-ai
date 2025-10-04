import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Family AI Companion',
  description: 'Arabic-first parenting assistant with cultural sensitivity.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>
        <header style={{ padding: '1.5rem', background: '#ffffff', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
          <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <a href="/" style={{ fontWeight: 700, fontSize: '1.5rem' }}>رفيق العائلة الذكي</a>
            <nav style={{ display: 'flex', gap: '1rem' }}>
              <a href="/chat">المحادثة</a>
              <a href="/profile">الملف العائلي</a>
              <a href="/admin/upload">لوحة المشرف</a>
            </nav>
          </div>
        </header>
        <main style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem 1.5rem' }}>{children}</main>
        <footer style={{ maxWidth: '960px', margin: '0 auto', padding: '2rem 1.5rem', fontSize: '0.875rem', color: '#6b7280' }}>
          تم بناء المنصة مع مراعاة الخصوصية والرحمة. يرجى مراجعة مختص بشري في المواضيع الحساسة.
        </footer>
      </body>
    </html>
  );
}
