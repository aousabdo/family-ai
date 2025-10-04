import ProfileForm from '@/components/ProfileForm';

export default function ProfilePage() {
  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      <div style={{ background: '#e0f2fe', padding: '1.25rem', borderRadius: '12px', color: '#0f172a' }}>
        <p style={{ margin: 0 }}>
          استخدم هذه الصفحة لإدارة ملف عائلتك، وإضافة الأطفال، والحصول على رمز الإدارة لاستعمال لوحة المشرف ورفع المحتوى الخاص بك.
        </p>
      </div>
      <ProfileForm />
    </div>
  );
}
