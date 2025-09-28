import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import { LogOut, User, Menu } from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';
import Glassmorphism from './ui/Glassmorphism';

const Header = ({ onMenuClick }) => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  return (
    <header className="bg-gradient-to-r from-slate-900/95 to-slate-800/95 backdrop-blur-md border-b border-white/10 px-4 md:px-6 py-4 sticky top-0 z-30">
      <div className="flex items-center justify-between max-w-full">
        <div className="flex items-center space-x-2 md:space-x-4 min-w-0 flex-1">
          {/* Mobile menu button */}
          <button
            onClick={onMenuClick}
            className="md:hidden p-3 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-accent-cyan focus:ring-offset-2 focus:ring-offset-slate-900 touch-manipulation active:scale-95"
            aria-label={t('header.toggle_nav')}
            aria-expanded="false"
          >
            <Menu className="w-6 h-6" aria-hidden="true" />
          </button>

          <Glassmorphism className="px-3 md:px-4 py-2 flex-shrink-0" variant="subtle" border={false}>
            <h1 className="text-lg md:text-xl font-semibold text-white truncate">
              {t('header.app_name')}
            </h1>
          </Glassmorphism>
        </div>
        <div className="flex items-center space-x-1 md:space-x-4 flex-shrink-0">
          <LanguageSwitcher variant="dropdown" />
          <Glassmorphism className="px-2 md:px-3 py-2" variant="subtle" border={false}>
            <div className="flex items-center space-x-2 text-gray-300" role="status" aria-label={`${t('header.logged_in_as')} ${user?.username || t('header.admin')}`}>
              <User className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span className="hidden sm:inline truncate max-w-20 md:max-w-none">{user?.username || t('header.admin')}</span>
            </div>
          </Glassmorphism>
          <Glassmorphism className="px-2 md:px-3 py-2" variant="subtle" border={false}>
            <button
              onClick={logout}
              className="flex items-center space-x-2 text-sm text-gray-300 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-accent-cyan focus:ring-offset-2 focus:ring-offset-slate-900 rounded touch-manipulation active:scale-95"
              aria-label={t('header.logout_from_app')}
            >
              <LogOut className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              <span className="hidden sm:inline">{t('common.close')}</span>
            </button>
          </Glassmorphism>
        </div>
      </div>
    </header>
  );
};

export default Header;