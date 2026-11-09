/** AI Chat tab: tool-calling chat arrives in M7. */

import { useTranslation } from 'react-i18next';

import { Placeholder } from '@/components/Placeholder';
import { Screen } from '@/components/Screen';

export default function ChatScreen() {
  const { t } = useTranslation();
  return (
    <Screen title={t('titles.chat')}>
      <Placeholder milestone="M7" />
    </Screen>
  );
}
