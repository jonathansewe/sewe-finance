/** Reports tab: charts and totals arrive in M5. */

import { useTranslation } from 'react-i18next';

import { Placeholder } from '@/components/Placeholder';
import { Screen } from '@/components/Screen';

export default function ReportsScreen() {
  const { t } = useTranslation();
  return (
    <Screen title={t('titles.reports')}>
      <Placeholder milestone="M5" />
    </Screen>
  );
}
