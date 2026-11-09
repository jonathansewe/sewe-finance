/** Receipt tab: camera scan and AI extraction arrive in M6. */

import { useTranslation } from 'react-i18next';

import { Placeholder } from '@/components/Placeholder';
import { Screen } from '@/components/Screen';

export default function ReceiptScreen() {
  const { t } = useTranslation();
  return (
    <Screen title={t('titles.receipt')}>
      <Placeholder milestone="M6" />
    </Screen>
  );
}
