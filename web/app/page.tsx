import TipCard from '@/components/TipCard';

async function loadTips() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api';
  try {
    const res = await fetch(`${apiBase}/tips?age_range=3-5`, { next: { revalidate: 0 } });
    if (!res.ok) return [];
    const data = (await res.json()) as { tips: string[] };
    return data.tips;
  } catch (error) {
    console.warn('Failed to load tips', error);
    return [];
  }
}

export default async function HomePage() {
  const tips = await loadTips();

  return (
    <section style={{ display: 'grid', gap: '1.5rem' }}>
      <div style={{ background: '#ffffff', borderRadius: '16px', padding: '2rem', boxShadow: '0 8px 24px rgba(15,23,42,0.08)' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>مرحباً بك في رفيق العائلة الذكي</h1>
        <p style={{ lineHeight: 1.7 }}>
          مساعد تربوي عربي يركز على الرفق، الثقافة المحلية، وسلامة الأسرة. اختر بين نبرة يزن الودودة أو المدرب المحايد
          لتتلقّى نصائح مخصصة لاحتياجات عائلتك.
        </p>
        <div style={{ marginTop: '1.5rem', padding: '1rem', borderRadius: '12px', background: '#fff7ed', fontSize: '0.95rem' }}>
          <strong>تنويه مهم:</strong> المواضيع المتعلقة بالعنف، الصحة النفسية، أو الطوارئ الطبية تتطلب تدخلاً بشرياً فورياً.
        </div>
      </div>
      <div style={{ display: 'grid', gap: '1rem' }}>
        {tips.length > 0 ? (
          tips.map((tip) => <TipCard key={tip} tip={tip} />)
        ) : (
          <TipCard tip="ابدأ اليوم بمحادثة قصيرة مع طفلك حول شعوره، وطمئنه بأنك موجود للاستماع دائماً." />
        )}
      </div>
    </section>
  );
}
