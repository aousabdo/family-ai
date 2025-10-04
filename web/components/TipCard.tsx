interface TipCardProps {
  tip: string;
}

export default function TipCard({ tip }: TipCardProps) {
  return (
    <article style={{ background: '#ffffff', borderRadius: '12px', padding: '1.25rem', boxShadow: '0 4px 18px rgba(148,163,184,0.25)' }}>
      <h3 style={{ marginTop: 0, marginBottom: '0.5rem', fontSize: '1rem', color: '#2563eb' }}>نصيحة يومية</h3>
      <p style={{ margin: 0, lineHeight: 1.7 }}>{tip}</p>
    </article>
  );
}
