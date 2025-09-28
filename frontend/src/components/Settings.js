import React from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from './ui/GlassCard';
import LanguageSwitcher from './LanguageSwitcher';

const Settings = () => {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white">{t('settings.title')}</h1>

      <GlassCard title={t('settings.language')}>
        <p className="text-gray-300 mb-4">{t('settings.language_description', 'Choose the language for the application interface.')}</p>
        <LanguageSwitcher />
      </GlassCard>

      <GlassCard title={t('settings.theme')}>
        <p className="text-gray-300">{t('settings.theme_description', 'Theme selection is not yet implemented.')}</p>
      </GlassCard>

      <GlassCard title={t('settings.notifications')}>
        <p className="text-gray-300">{t('settings.notifications_description', 'Notification settings are not yet implemented.')}</p>
      </GlassCard>
    </div>
  );
};

export default Settings;