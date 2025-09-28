import React from 'react';
import { useTranslation } from 'react-i18next';
import GlassButton from './ui/GlassButton';

const LanguageSwitcher = ({ variant = 'button', className = '' }) => {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'ru', name: 'Русский', flag: '🇷🇺' }
  ];

  const handleLanguageChange = (langCode) => {
    i18n.changeLanguage(langCode);
    localStorage.setItem('language', langCode);
  };

  if (variant === 'dropdown') {
    return (
      <div className={`relative ${className}`}>
        <select
          value={i18n.language}
          onChange={(e) => handleLanguageChange(e.target.value)}
          className="bg-transparent border border-white/20 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-white/20"
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code} className="bg-gray-900">
              {lang.flag} {lang.name}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-1 ${className}`}>
      {languages.map((lang) => (
        <GlassButton
          key={lang.code}
          variant={i18n.language === lang.code ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => handleLanguageChange(lang.code)}
          className="text-xs"
        >
          {lang.flag}
        </GlassButton>
      ))}
    </div>
  );
};

export default LanguageSwitcher;