import Chat from '@/components/Chat';

import styles from './page.module.css';

export default function ChatPage() {
  return (
    <div className={styles.page}>
      <h1 className={styles.title}>المحادثة الذكية</h1>
      <Chat />
    </div>
  );
}
