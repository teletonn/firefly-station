import React, { useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Users, MessageSquare, Settings, FileText, BarChart3, Map, MapPin, UserCheck, AlertTriangle, Cog, Workflow, TrendingUp, X } from 'lucide-react';

const Sidebar = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { t } = useTranslation();

  // Close sidebar when route changes on mobile
  useEffect(() => {
    if (window.innerWidth < 768) {
      onClose();
    }
  }, [location.pathname, onClose]);

  // Close sidebar on escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const menuItems = [
    { path: '/', icon: BarChart3, labelKey: 'nav.dashboard' },
    { path: '/analytics', icon: TrendingUp, labelKey: 'nav.analytics' },
    { path: '/users', icon: Users, labelKey: 'nav.users' },
    { path: '/user-groups', icon: UserCheck, labelKey: 'nav.userGroups' },
    { path: '/alerts', icon: AlertTriangle, labelKey: 'nav.alerts' },
    { path: '/alert-config', icon: Cog, labelKey: 'nav.alertConfig' },
    { path: '/processes', icon: Workflow, labelKey: 'nav.processes' },
    { path: '/messages', icon: MessageSquare, labelKey: 'nav.messages' },
    { path: '/map', icon: Map, labelKey: 'nav.map' },
    { path: '/zones', icon: MapPin, labelKey: 'nav.zones' },
    { path: '/bot-controls', icon: Settings, labelKey: 'nav.settings' },
    { path: '/bot-templates', icon: MessageSquare, labelKey: 'nav.botTemplates' },
    { path: '/audit', icon: FileText, labelKey: 'nav.audit' },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden touch-manipulation"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed md:static inset-y-0 left-0 z-50
        w-64 md:w-64 bg-gradient-to-b from-slate-900/95 to-slate-800/95 backdrop-blur-md
        border-r border-white/10 transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        md:h-screen min-h-screen-safe
      `}>
        {/* Mobile close button */}
        <div className="flex justify-between items-center p-4 md:hidden">
          <h2 className="text-xl font-bold text-white">{t('sidebar.admin_panel')}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
            aria-label={t('sidebar.close_nav_menu')}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Desktop header */}
        <div className="hidden md:block p-6">
          <h2 className="text-xl font-bold text-white">{t('sidebar.admin_panel')}</h2>
        </div>

        <nav className="mt-6 px-2 md:px-0" role="navigation" aria-label={t('sidebar.main_nav')}>
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 md:px-6 py-4 md:py-3 mx-2 md:mx-0 text-sm font-medium transition-all duration-200 rounded-lg md:rounded-none focus:outline-none focus:ring-2 focus:ring-accent-cyan focus:ring-offset-2 focus:ring-offset-slate-900 touch-manipulation ${
                  isActive
                    ? 'text-blue-400 bg-white/10 border-r-2 border-blue-400 md:border-r-2'
                    : 'text-gray-300 hover:text-white hover:bg-white/5 active:bg-white/10'
                }`}
                aria-current={isActive ? 'page' : undefined}
                aria-label={`${t(item.labelKey)} ${isActive ? t('sidebar.current_page') : ''}`}
                tabIndex={0}
              >
                <Icon className="w-5 h-5 mr-3 flex-shrink-0" aria-hidden="true" />
                <span>{t(item.labelKey)}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
};

export default Sidebar;