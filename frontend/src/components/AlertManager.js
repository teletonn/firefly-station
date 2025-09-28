import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';

const AlertManager = () => {
  const { t } = useTranslation();
  const { subscribe } = useWebSocket();
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('active');
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [filters, setFilters] = useState({
    type: '',
    severity: '',
    zone: '',
    user: ''
  });

  // Form state for creating alerts
  const [alertForm, setAlertForm] = useState({
    title: '',
    message: '',
    alert_type: 'custom',
    severity: 'medium',
    user_id: '',
    zone_id: '',
    target_groups: []
  });

  useEffect(() => {
    fetchAlerts();
    fetchStats();
  }, [activeTab, filters]);

  // Subscribe to real-time alert updates
  useEffect(() => {
    const unsubscribeNewAlert = subscribe('new_alert', (message) => {
      const newAlert = message.data;
      setAlerts(prev => [newAlert, ...prev]);
      setStats(prev => ({
        ...prev,
        total_alerts: (prev.total_alerts || 0) + 1,
        unacknowledged_alerts: (prev.unacknowledged_alerts || 0) + 1
      }));
    });

    const unsubscribeStatsUpdate = subscribe('statistics_update', (message) => {
      if (message.data.alert_stats) {
        setStats(prev => ({
          ...prev,
          ...message.data.alert_stats
        }));
      }
    });

    return () => {
      unsubscribeNewAlert();
      unsubscribeStatsUpdate();
    };
  }, [subscribe]);

  const fetchAlerts = async () => {
    try {
      const params = new URLSearchParams({
        include_acknowledged: activeTab === 'history' ? 'true' : 'false',
        limit: '100'
      });

      if (filters.type) params.append('alert_type', filters.type);
      if (filters.severity) params.append('severity', filters.severity);
      if (filters.zone) params.append('zone_id', filters.zone);
      if (filters.user) params.append('user_id', filters.user);

      const response = await fetch(`/api/alerts/?${params}`);
      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/alerts/stats/overview');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    try {
      const response = await fetch(`/api/alerts/${alertId}/acknowledge`, {
        method: 'PUT'
      });

      if (response.ok) {
        fetchAlerts();
        fetchStats();
      }
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  const handleResolveAlert = async (alertId, notes = '') => {
    try {
      const response = await fetch(`/api/alerts/${alertId}/resolve`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ resolution_notes: notes })
      });

      if (response.ok) {
        fetchAlerts();
        fetchStats();
      }
    } catch (error) {
      console.error('Error resolving alert:', error);
    }
  };

  const handleCreateAlert = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/alerts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(alertForm),
      });

      if (response.ok) {
        setShowCreateModal(false);
        setAlertForm({
          title: '',
          message: '',
          alert_type: 'custom',
          severity: 'medium',
          user_id: '',
          zone_id: '',
          target_groups: []
        });
        fetchAlerts();
        fetchStats();
      }
    } catch (error) {
      console.error('Error creating alert:', error);
    }
  };

  const getSeverityBadgeColor = (severity) => {
    const colors = {
      low: 'bg-green-400/20 text-green-400 border-green-400/30',
      medium: 'bg-yellow-400/20 text-yellow-400 border-yellow-400/30',
      high: 'bg-orange-400/20 text-orange-400 border-orange-400/30',
      critical: 'bg-red-400/20 text-red-400 border-red-400/30'
    };
    return colors[severity] || 'bg-gray-400/20 text-gray-400 border-gray-400/30';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
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
        <h1 className="text-3xl font-bold text-white">{t('alerts.management')}</h1>
        <GlassButton
          onClick={() => setShowCreateModal(true)}
          variant="primary"
          className="flex items-center space-x-2"
        >
          <span>+</span>
          <span>{t('alerts.create_alert')}</span>
        </GlassButton>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total_alerts || 0}</div>
          <div className="text-sm text-gray-400">{t('alerts.total')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-red-400">{stats.unacknowledged_alerts || 0}</div>
          <div className="text-sm text-gray-400">{t('alerts.unacknowledged')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-yellow-400">{stats.unresolved_alerts || 0}</div>
          <div className="text-sm text-gray-400">{t('alerts.unresolved')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-green-400">{stats.recent_alerts || 0}</div>
          <div className="text-sm text-gray-400">{t('alerts.recent')}</div>
        </GlassCard>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-800/50 p-1 rounded-lg">
        {[
          { id: 'active', label: t('alerts.active') },
          { id: 'history', label: t('alerts.history') }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-accent-cyan text-dark-900'
                : 'text-gray-300 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filters */}
      <GlassCard>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t('alerts.type')}</label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
            >
              <option value="">{t('alerts.all_types')}</option>
              <option value="zone_entry">{t('alerts.zone_entry')}</option>
              <option value="zone_exit">{t('alerts.zone_exit')}</option>
              <option value="speeding">{t('alerts.speeding')}</option>
              <option value="battery_low">{t('alerts.battery_low')}</option>
              <option value="offline">{t('alerts.offline')}</option>
              <option value="custom">{t('alerts.custom')}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t('alerts.severity')}</label>
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
            >
              <option value="">{t('alerts.severity.all')}</option>
              <option value="low">{t('alerts.severity.low')}</option>
              <option value="medium">{t('alerts.severity.medium')}</option>
              <option value="high">{t('alerts.severity.high')}</option>
              <option value="critical">{t('alerts.severity.critical')}</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t('zones.name')}</label>
            <input
              type="text"
              value={filters.zone}
              onChange={(e) => setFilters({ ...filters, zone: e.target.value })}
              placeholder={t('alerts.zone_id')}
              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">{t('users.name')}</label>
            <input
              type="text"
              value={filters.user}
              onChange={(e) => setFilters({ ...filters, user: e.target.value })}
              placeholder={t('alerts.user_id')}
              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
            />
          </div>
        </div>
      </GlassCard>

      {/* Alerts List */}
      <GlassCard>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors cursor-pointer"
              onClick={() => {
                setSelectedAlert(alert);
                setShowDetailsModal(true);
              }}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">{alert.title}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getSeverityBadgeColor(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    <span className="px-2 py-1 bg-dark-700 text-gray-300 rounded-full text-xs">
                      {alert.alert_type.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  <p className="text-gray-300 text-sm mb-2">{alert.message}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>{t('alerts.user')}: {alert.user_name || alert.user_id}</span>
                    {alert.zone_name && <span>{t('alerts.zone')}: {alert.zone_name}</span>}
                    <span>{formatTimestamp(alert.created_at)}</span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  {!alert.is_acknowledged && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAcknowledgeAlert(alert.id);
                      }}
                      className="px-3 py-1 bg-accent-cyan text-dark-900 rounded text-sm font-medium hover:bg-accent-cyan/80"
                    >
                      {t('alerts.acknowledge')}
                    </button>
                  )}
                  {!alert.is_resolved && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleResolveAlert(alert.id);
                      }}
                      className="px-3 py-1 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-500"
                    >
                      {t('alerts.resolve')}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {alerts.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('alerts.no_alerts')}</p>
          )}
        </div>
      </GlassCard>

      {/* Create Alert Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <form onSubmit={handleCreateAlert}>
              <h2 className="text-xl font-bold text-white mb-4">{t('alerts.create_new_alert')}</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    {t('alerts.message')}
                  </label>
                  <input
                    type="text"
                    value={alertForm.title}
                    onChange={(e) => setAlertForm({ ...alertForm, title: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    {t('alerts.alertType')}
                  </label>
                  <select
                    value={alertForm.alert_type}
                    onChange={(e) => setAlertForm({ ...alertForm, alert_type: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="custom">{t('alerts.custom')}</option>
                    <option value="emergency">{t('alerts.emergency')}</option>
                    <option value="maintenance">{t('alerts.maintenance')}</option>
                    <option value="info">{t('alerts.info')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    {t('alerts.severity')}
                  </label>
                  <select
                    value={alertForm.severity}
                    onChange={(e) => setAlertForm({ ...alertForm, severity: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="low">{t('alerts.severity.low')}</option>
                    <option value="medium">{t('alerts.severity.medium')}</option>
                    <option value="high">{t('alerts.severity.high')}</option>
                    <option value="critical">{t('alerts.severity.critical')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    {t('alerts.target_user')}
                  </label>
                  <input
                    type="text"
                    value={alertForm.user_id}
                    onChange={(e) => setAlertForm({ ...alertForm, user_id: e.target.value })}
                    placeholder={t('alerts.user_id')}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('alerts.message')}
                </label>
                <textarea
                  value={alertForm.message}
                  onChange={(e) => setAlertForm({ ...alertForm, message: e.target.value })}
                  rows={4}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  required
                />
              </div>

              <div className="flex space-x-3 mt-6">
                <GlassButton type="submit" variant="primary">
                  {t('alerts.create_alert')}
                </GlassButton>
                <GlassButton
                  type="button"
                  variant="secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  {t('common.cancel')}
                </GlassButton>
              </div>
            </form>
          </GlassCard>
        </div>
      )}

      {/* Alert Details Modal */}
      {showDetailsModal && selectedAlert && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('alerts.alert_details')}</h2>
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.message')}</label>
                  <p className="text-white">{selectedAlert.title}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.severity')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getSeverityBadgeColor(selectedAlert.severity)}`}>
                    {t(`alerts.severity.${selectedAlert.severity}`)}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.type')}</label>
                  <p className="text-white">{t(`alerts.${selectedAlert.alert_type}`)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.status')}</label>
                  <div className="flex space-x-2">
                    <span className={`px-2 py-1 rounded text-xs ${selectedAlert.is_acknowledged ? 'bg-green-600' : 'bg-red-600'}`}>
                      {selectedAlert.is_acknowledged ? t('alerts.acknowledged') : t('alerts.unacknowledged')}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${selectedAlert.is_resolved ? 'bg-green-600' : 'bg-yellow-600'}`}>
                      {selectedAlert.is_resolved ? t('alerts.resolved') : t('alerts.unresolved')}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.message')}</label>
                <p className="text-white bg-dark-800/50 p-3 rounded">{selectedAlert.message}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.user')}</label>
                  <p className="text-white">{selectedAlert.user_name || selectedAlert.user_id}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.zone')}</label>
                  <p className="text-white">{selectedAlert.zone_name || t('alerts.n_a')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.created')}</label>
                  <p className="text-white">{formatTimestamp(selectedAlert.created_at)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.acknowledged')}</label>
                  <p className="text-white">
                    {selectedAlert.acknowledged_at ? formatTimestamp(selectedAlert.acknowledged_at) : t('alerts.unacknowledged').toLowerCase()}
                  </p>
                </div>
              </div>

              {selectedAlert.acknowledged_by_username && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('alerts.acknowledged_by')}</label>
                  <p className="text-white">{selectedAlert.acknowledged_by_username}</p>
                </div>
              )}

              <div className="flex space-x-3 pt-4">
                {!selectedAlert.is_acknowledged && (
                  <GlassButton
                    onClick={() => {
                      handleAcknowledgeAlert(selectedAlert.id);
                      setShowDetailsModal(false);
                    }}
                    variant="primary"
                  >
                    {t('alerts.acknowledge')}
                  </GlassButton>
                )}
                {!selectedAlert.is_resolved && (
                  <GlassButton
                    onClick={() => {
                      handleResolveAlert(selectedAlert.id, t('alerts.resolved_from_details'));
                      setShowDetailsModal(false);
                    }}
                    variant="secondary"
                  >
                    {t('alerts.resolve')}
                  </GlassButton>
                )}
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default AlertManager;