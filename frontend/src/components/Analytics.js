import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';
import axios from 'axios';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Users,
  MessageSquare,
  AlertTriangle,
  MapPin,
  Bot,
  Activity,
  Download,
  RefreshCw
} from 'lucide-react';

// Chart colors constant
const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

const Analytics = () => {
  const { t } = useTranslation();
  const { isConnected, subscribe } = useWebSocket();
  const [activeTab, setActiveTab] = useState('overview');
  const [period, setPeriod] = useState('7d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState({
    overview: {},
    users: {},
    messages: {},
    alerts: {},
    geolocation: {},
    performance: {}
  });

  useEffect(() => {
    fetchAnalyticsData();
  }, [period]);

  // Subscribe to real-time analytics updates
  useEffect(() => {
    const unsubscribeAnalyticsUpdate = subscribe('analytics_update', (message) => {
      if (message.data.analytics_data) {
        setData(prev => ({
          ...prev,
          ...message.data.analytics_data
        }));
      }
    });

    const unsubscribeStatsUpdate = subscribe('statistics_update', (message) => {
      if (message.data.analytics_stats) {
        setData(prev => ({
          ...prev,
          ...message.data.analytics_stats
        }));
      }
    });

    return () => {
      unsubscribeAnalyticsUpdate();
      unsubscribeStatsUpdate();
    };
  }, [subscribe]);

  const fetchAnalyticsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const endpoints = [
        'dashboard/overview',
        `users/analytics?period=${period}`,
        `messages/analytics?period=${period}`,
        `alerts/analytics?period=${period}`,
        `geolocation/analytics?period=${period}`,
        `performance/metrics?period=${period.replace('d', '')}d`
      ];

      const responses = await Promise.all(
        endpoints.map(endpoint => axios.get(`/api/analytics/${endpoint}`))
      );

      const results = responses.map(response => response.data);

      setData({
        overview: results[0],
        users: results[1],
        messages: results[2],
        alerts: results[3],
        geolocation: results[4],
        performance: results[5]
      });
    } catch (error) {
      console.error('Error fetching analytics data:', error);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const generateReport = async () => {
    try {
      const response = await axios.get(`/api/analytics/reports/generate?report_type=daily`);
      const reportData = response.data;

      // Create and download JSON report
      const blob = new Blob([JSON.stringify(reportData, null, 2)], {
        type: 'application/json'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics-report-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating report:', error);
    }
  };

  const tabs = [
    { id: 'overview', label: t('analytics.overview'), icon: Activity },
    { id: 'users', label: t('analytics.users'), icon: Users },
    { id: 'messages', label: t('analytics.messages'), icon: MessageSquare },
    { id: 'alerts', label: t('analytics.alerts'), icon: AlertTriangle },
    { id: 'geolocation', label: t('analytics.geolocation'), icon: MapPin },
    { id: 'performance', label: t('analytics.performance'), icon: Bot }
  ];

  const periodOptions = [
    { value: '1h', label: t('analytics.last_hour') },
    { value: '24h', label: t('analytics.last_24_hours') },
    { value: '7d', label: t('analytics.last_7_days') },
    { value: '30d', label: t('analytics.last_30_days') },
    { value: '90d', label: t('analytics.last_90_days') }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-red-400 font-medium">Error</span>
            </div>
            <GlassButton
              onClick={() => {
                setError(null);
                fetchAnalyticsData();
              }}
              variant="secondary"
              className="text-sm"
            >
              Retry
            </GlassButton>
          </div>
          <p className="text-red-300 mt-2">{error}</p>
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">{t('analytics.title')}</h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-sm text-gray-400">
              {isConnected ? t('analytics.live_data') : t('analytics.offline')}
            </span>
          </div>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
          >
            {periodOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          <GlassButton onClick={fetchAnalyticsData} variant="ghost" size="sm">
            <RefreshCw className="w-4 h-4" />
          </GlassButton>
          <GlassButton onClick={generateReport} variant="primary" size="sm">
            <Download className="w-4 h-4 mr-2" />
            {t('analytics.export_report')}
          </GlassButton>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-800/50 p-1 rounded-lg">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-accent-cyan text-dark-900'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="space-y-6">
        {activeTab === 'overview' && <OverviewTab data={data.overview} />}
        {activeTab === 'users' && <UsersTab data={data.users} />}
        {activeTab === 'messages' && <MessagesTab data={data.messages} />}
        {activeTab === 'alerts' && <AlertsTab data={data.alerts} />}
        {activeTab === 'geolocation' && <GeolocationTab data={data.geolocation} />}
        {activeTab === 'performance' && <PerformanceTab data={data.performance} />}
      </div>
    </div>
  );
};

// Overview Tab Component
const OverviewTab = ({ data }) => {
  const { t } = useTranslation();
  const overviewData = data || {};

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title={t('analytics.total_users')}
          value={overviewData.users?.total || 0}
          change={overviewData.users?.trend}
          icon={Users}
          color="blue"
        />
        <MetricCard
          title={t('analytics.messages_today')}
          value={overviewData.messages?.total_today || 0}
          change={overviewData.messages?.trend}
          icon={MessageSquare}
          color="green"
        />
        <MetricCard
          title={t('analytics.active_alerts')}
          value={overviewData.alerts?.total_active || 0}
          change={overviewData.alerts?.trend}
          icon={AlertTriangle}
          color="red"
        />
        <MetricCard
          title={t('analytics.active_zones')}
          value={overviewData.zones?.active || 0}
          icon={MapPin}
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.user_activity_trends')}>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={overviewData.userActivityTrends || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Area
                type="monotone"
                dataKey="active_users"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard title={t('analytics.alert_distribution')}>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={[
                  { name: t('analytics.low'), value: overviewData.alerts?.by_severity?.low || 0 },
                  { name: t('analytics.medium'), value: overviewData.alerts?.by_severity?.medium || 0 },
                  { name: t('analytics.high'), value: overviewData.alerts?.by_severity?.high || 0 },
                  { name: t('analytics.critical'), value: overviewData.alerts?.by_severity?.critical || 0 }
                ]}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {[
                  { name: 'Low', value: overviewData.alerts?.by_severity?.low || 0 },
                  { name: 'Medium', value: overviewData.alerts?.by_severity?.medium || 0 },
                  { name: 'High', value: overviewData.alerts?.by_severity?.high || 0 },
                  { name: 'Critical', value: overviewData.alerts?.by_severity?.critical || 0 }
                ].map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>
    </div>
  );
};

// Users Tab Component
const UsersTab = ({ data }) => {
  const { t } = useTranslation();
  const userData = data || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.user_registration_trends')}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={userData.registration_trends || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: '#10b981' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard title={t('analytics.user_activity_patterns')}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={userData.activity_patterns || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="hour" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="activity_count" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard title={t('analytics.device_statistics')}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(userData.device_stats || {}).map(([device, count]) => (
            <div key={device} className="text-center">
              <div className="text-2xl font-bold text-white">{count}</div>
              <div className="text-sm text-gray-400 capitalize">{device}</div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};

// Messages Tab Component
const MessagesTab = ({ data }) => {
  const { t } = useTranslation();
  const messageData = data || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.message_volume_trends')}>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={messageData.volume_trends || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="#f59e0b"
                fill="#f59e0b"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard title={t('analytics.message_types_distribution')}>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={Object.entries(messageData.type_distribution || {}).map(([type, count]) => ({
                  name: type,
                  value: count
                }))}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {Object.entries(messageData.type_distribution || {}).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {messageData.response_times?.avg_response_time?.toFixed(0) || 0}ms
          </div>
          <div className="text-sm text-gray-400">{t('analytics.avg_response_time')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {messageData.bot_quality?.success_rate?.toFixed(1) || 0}%
          </div>
          <div className="text-sm text-gray-400">{t('analytics.bot_success_rate')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {messageData.bot_quality?.total_interactions || 0}
          </div>
          <div className="text-sm text-gray-400">{t('analytics.bot_interactions')}</div>
        </GlassCard>
      </div>
    </div>
  );
};

// Alerts Tab Component
const AlertsTab = ({ data }) => {
  const { t } = useTranslation();
  const alertData = data || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.alert_trends')}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={alertData.alert_trends || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#ef4444"
                strokeWidth={2}
                dot={{ fill: '#ef4444' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard title={t('analytics.alert_types')}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={Object.entries(alertData.type_distribution || {}).map(([type, count]) => ({
              type: type.replace('_', ' '),
              count
            }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="type" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="count" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard title={t('analytics.zone_based_alerts')}>
        <div className="space-y-3">
          {(alertData.zone_alerts || []).map((zone, index) => (
            <div key={index} className="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg">
              <span className="text-white">{zone.zone}</span>
              <span className="text-accent-cyan font-semibold">{zone.count} {t('analytics.alerts')}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};

// Geolocation Tab Component
const GeolocationTab = ({ data }) => {
  const { t } = useTranslation();
  const geoData = data || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.movement_patterns')}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={(geoData.movement_patterns || []).slice(0, 10)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="user_id" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="updates" fill="#06b6d4" />
            </BarChart>
          </ResponsiveContainer>
        </GlassCard>

        <GlassCard title={t('analytics.speed_distribution')}>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={Object.entries(geoData.speed_analysis || {}).map(([speed, count]) => ({
                  name: speed.replace('_', ' '),
                  value: count
                }))}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {Object.entries(geoData.speed_analysis || {}).map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </GlassCard>
      </div>

      <GlassCard title={t('analytics.zone_dwell_times')}>
        <div className="space-y-3">
          {(geoData.dwell_times || []).map((zone, index) => (
            <div key={index} className="flex justify-between items-center p-3 bg-dark-800/30 rounded-lg">
              <div>
                <div className="text-white font-medium">{zone.zone_name}</div>
                <div className="text-sm text-gray-400">{zone.users} {t('analytics.users')}</div>
              </div>
              <div className="text-right">
                <div className="text-accent-cyan font-semibold">
                  {zone.avg_dwell_hours.toFixed(1)}{t('analytics.h_avg')}
                </div>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};

// Performance Tab Component
const PerformanceTab = ({ data }) => {
  const { t } = useTranslation();
  const perfData = data || {};

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {perfData.system_performance?.cpu_usage?.toFixed(1) || 0}%
          </div>
          <div className="text-sm text-gray-400">{t('analytics.cpu_usage')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {perfData.system_performance?.memory_usage?.toFixed(1) || 0}%
          </div>
          <div className="text-sm text-gray-400">{t('analytics.memory_usage')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {perfData.api_response_times?.avg_response_time?.toFixed(0) || 0}ms
          </div>
          <div className="text-sm text-gray-400">{t('analytics.api_response_time')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">
            {perfData.websocket_metrics?.active_connections || 0}
          </div>
          <div className="text-sm text-gray-400">{t('analytics.active_connections')}</div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard title={t('analytics.database_performance')}>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.query_count')}</span>
              <span className="text-white font-semibold">{perfData.database_performance?.query_count || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.avg_query_time')}</span>
              <span className="text-white font-semibold">{perfData.database_performance?.avg_query_time?.toFixed(1) || 0}ms</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.slow_queries')}</span>
              <span className="text-white font-semibold">{perfData.database_performance?.slow_queries || 0}</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard title={t('analytics.websocket_metrics')}>
          <div className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.messages_per_sec')}</span>
              <span className="text-white font-semibold">{perfData.websocket_metrics?.messages_per_second?.toFixed(1) || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.connection_drops')}</span>
              <span className="text-white font-semibold">{perfData.websocket_metrics?.connection_drops || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{t('analytics.avg_session_duration')}</span>
              <span className="text-white font-semibold">{((perfData.websocket_metrics?.avg_session_duration || 0) / 60).toFixed(0)}{t('analytics.min')}</span>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
};

// Metric Card Component
const MetricCard = ({ title, value, change, icon: Icon, color }) => {
  const { t } = useTranslation();
  const colorClasses = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    purple: 'text-purple-400'
  };

  return (
    <GlassCard className="text-center">
      <Icon className={`w-8 h-8 mx-auto mb-2 ${colorClasses[color]}`} />
      <div className="text-2xl font-bold text-white">{value.toLocaleString()}</div>
      <div className="text-sm text-gray-400">{title}</div>
      {change && (
        <div className={`flex items-center justify-center mt-2 text-xs ${
          change.direction === 'up' ? 'text-green-400' : change.direction === 'down' ? 'text-red-400' : 'text-gray-400'
        }`}>
          {change.direction === 'up' && <TrendingUp className="w-3 h-3 mr-1" />}
          {change.direction === 'down' && <TrendingDown className="w-3 h-3 mr-1" />}
          <span>{change.percentage}{t(change.direction === 'up' ? 'analytics.up' : 'analytics.down')}</span>
        </div>
      )}
    </GlassCard>
  );
};

export default Analytics;