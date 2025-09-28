import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';
import {
  Search,
  Filter,
  Download,
  RefreshCw,
  Eye,
  User,
  Activity,
  Calendar,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const AuditLogs = () => {
  const { t } = useTranslation();
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  // Filter states
  const [filters, setFilters] = useState({
    action: '',
    resource: '',
    admin_user_id: '',
    start_date: '',
    end_date: ''
  });

  const logsPerPage = 50;

  useEffect(() => {
    fetchAuditLogs();
    fetchStats();
  }, [currentPage, filters]);

  const fetchAuditLogs = async () => {
    try {
      const params = new URLSearchParams({
        limit: logsPerPage.toString(),
        offset: ((currentPage - 1) * logsPerPage).toString()
      });

      if (filters.action) params.append('action', filters.action);
      if (filters.resource) params.append('resource', filters.resource);
      if (filters.admin_user_id) params.append('admin_user_id', filters.admin_user_id);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);

      const response = await fetch(`/api/audit/?${params}`);
      const data = await response.json();
      setLogs(data.logs || []);
      setTotalPages(Math.ceil((data.total || 0) / logsPerPage));
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/audit/stats/overview');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching audit stats:', error);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters({ ...filters, [field]: value });
    setCurrentPage(1); // Reset to first page when filtering
  };

  const clearFilters = () => {
    setFilters({
      action: '',
      resource: '',
      admin_user_id: '',
      start_date: '',
      end_date: ''
    });
    setCurrentPage(1);
  };

  const exportLogs = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.action) params.append('action', filters.action);
      if (filters.resource) params.append('resource', filters.resource);
      if (filters.admin_user_id) params.append('admin_user_id', filters.admin_user_id);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);

      const response = await fetch(`/api/audit/?${params}&limit=1000`);
      const data = await response.json();

      const csvContent = [
        ['Timestamp', 'User', 'Action', 'Resource', 'Resource ID', 'Details', 'IP Address'].join(','),
        ...data.logs.map(log => [
          log.timestamp,
          log.username || 'Unknown',
          log.action,
          log.resource,
          log.resource_id || '',
          `"${(log.details || '').replace(/"/g, '""')}"`,
          log.ip_address || ''
        ].join(','))
      ].join('\n');

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error exporting logs:', error);
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getActionColor = (action) => {
    const colors = {
      create: 'text-green-400 bg-green-400/10',
      update: 'text-blue-400 bg-blue-400/10',
      delete: 'text-red-400 bg-red-400/10',
      view: 'text-gray-400 bg-gray-400/10',
      login: 'text-purple-400 bg-purple-400/10',
      logout: 'text-orange-400 bg-orange-400/10'
    };
    return colors[action] || 'text-gray-400 bg-gray-400/10';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">{t('auditLogs.title')}</h1>
        <div className="flex items-center space-x-3">
          <GlassButton
            onClick={() => setShowFilters(!showFilters)}
            variant="ghost"
            size="sm"
          >
            <Filter className="w-4 h-4 mr-2" />
            {t('auditLogs.filters')}
          </GlassButton>
          <GlassButton onClick={exportLogs} variant="primary" size="sm">
            <Download className="w-4 h-4 mr-2" />
            {t('auditLogs.export')}
          </GlassButton>
          <GlassButton onClick={fetchAuditLogs} variant="ghost" size="sm">
            <RefreshCw className="w-4 h-4" />
          </GlassButton>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total_logs || 0}</div>
          <div className="text-sm text-gray-400">{t('auditLogs.total_logs')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-green-400">{stats.recent_logs || 0}</div>
          <div className="text-sm text-gray-400">{t('auditLogs.recent_logs')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-blue-400">{stats.action_breakdown?.length || 0}</div>
          <div className="text-sm text-gray-400">{t('auditLogs.unique_actions')}</div>
        </GlassCard>
      </div>

      {/* Filters */}
      {showFilters && (
        <GlassCard>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('auditLogs.action')}
              </label>
              <select
                value={filters.action}
                onChange={(e) => handleFilterChange('action', e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              >
                <option value="">{t('auditLogs.all_actions')}</option>
                <option value="create">{t('auditLogs.create')}</option>
                <option value="update">{t('auditLogs.update')}</option>
                <option value="delete">{t('auditLogs.delete')}</option>
                <option value="view">{t('auditLogs.view')}</option>
                <option value="login">{t('auditLogs.login')}</option>
                <option value="logout">{t('auditLogs.logout')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('auditLogs.resource')}
              </label>
              <select
                value={filters.resource}
                onChange={(e) => handleFilterChange('resource', e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              >
                <option value="">{t('auditLogs.all_resources')}</option>
                <option value="user">{t('auditLogs.user')}</option>
                <option value="alert">{t('auditLogs.alert')}</option>
                <option value="zone">{t('auditLogs.zone')}</option>
                <option value="audit_logs">{t('auditLogs.audit_logs')}</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('auditLogs.start_date')}
              </label>
              <input
                type="datetime-local"
                value={filters.start_date}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('auditLogs.end_date')}
              </label>
              <input
                type="datetime-local"
                value={filters.end_date}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              />
            </div>

            <div className="flex items-end">
              <GlassButton onClick={clearFilters} variant="secondary" className="w-full">
                {t('auditLogs.clear_filters')}
              </GlassButton>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Logs Table */}
      <GlassCard>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-dark-600">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.timestamp')}
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.user')}
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.action')}
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.resource')}
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.details')}
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">
                  {t('auditLogs.actions')}
                </th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-dark-700 hover:bg-dark-800/30">
                  <td className="py-3 px-4 text-sm text-gray-300">
                    {formatTimestamp(log.timestamp)}
                  </td>
                  <td className="py-3 px-4 text-sm text-white">
                    {log.username || 'Unknown'}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionColor(log.action)}`}>
                      {log.action.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-300">
                    {log.resource}
                    {log.resource_id && (
                      <span className="text-accent-cyan ml-1">#{log.resource_id}</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-400 max-w-xs truncate">
                    {log.details}
                  </td>
                  <td className="py-3 px-4">
                    <button
                      onClick={() => {
                        setSelectedLog(log);
                        setShowDetailsModal(true);
                      }}
                      className="text-accent-cyan hover:text-accent-cyan/80 text-sm"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {logs.length === 0 && (
          <p className="text-gray-400 text-center py-8">{t('auditLogs.no_logs')}</p>
        )}
      </GlassCard>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-400">
            {t('auditLogs.page')} {currentPage} {t('auditLogs.of')} {totalPages}
          </div>
          <div className="flex items-center space-x-2">
            <GlassButton
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              variant="ghost"
              size="sm"
            >
              <ChevronLeft className="w-4 h-4" />
            </GlassButton>
            <GlassButton
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              variant="ghost"
              size="sm"
            >
              <ChevronRight className="w-4 h-4" />
            </GlassButton>
          </div>
        </div>
      )}

      {/* Details Modal */}
      {showDetailsModal && selectedLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('auditLogs.log_details')}</h2>
              <button
                onClick={() => setShowDetailsModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    {t('auditLogs.timestamp')}
                  </label>
                  <p className="text-white">{formatTimestamp(selectedLog.timestamp)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    {t('auditLogs.user')}
                  </label>
                  <p className="text-white">{selectedLog.username || 'Unknown'}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    {t('auditLogs.action')}
                  </label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionColor(selectedLog.action)}`}>
                    {selectedLog.action.toUpperCase()}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    {t('auditLogs.resource')}
                  </label>
                  <p className="text-white">
                    {selectedLog.resource}
                    {selectedLog.resource_id && (
                      <span className="text-accent-cyan ml-1">#{selectedLog.resource_id}</span>
                    )}
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  {t('auditLogs.details')}
                </label>
                <p className="text-white bg-dark-800/50 p-3 rounded whitespace-pre-wrap">
                  {selectedLog.details}
                </p>
              </div>

              {selectedLog.ip_address && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    {t('auditLogs.ip_address')}
                  </label>
                  <p className="text-white">{selectedLog.ip_address}</p>
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;