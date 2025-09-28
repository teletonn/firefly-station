import React, { useState, useEffect, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import { SkeletonCard } from './ui/Skeleton';
import { Users, Activity, MessageSquare, Bot, AlertTriangle, MapPin, Zap } from 'lucide-react';
import axios from 'axios';

const Dashboard = () => {
  const { t } = useTranslation();
  const { subscribe, isConnected } = useWebSocket();
  const [stats, setStats] = useState({
    total_users: 0,
    active_sessions: 0,
    messages_today: 0,
    bot_status: 'Offline',
    total_alerts: 0,
    active_zones: 0,
    online_users: 0
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial stats
  useEffect(() => {
    fetchStats();
    fetchRecentActivity();
  }, []);

  // Subscribe to real-time updates
  useEffect(() => {
    const unsubscribeStats = subscribe('statistics_update', (message) => {
      setStats(prev => ({
        ...prev,
        ...message.data.bot_stats,
        total_alerts: message.data.alert_stats?.total_alerts || prev.total_alerts,
        active_zones: message.data.zone_stats?.active_zones || prev.active_zones
      }));
    });

    const unsubscribeNewMessage = subscribe('new_message', (message) => {
      setStats(prev => ({
        ...prev,
        messages_today: prev.messages_today + 1
      }));
      addRecentActivity('message', `${t('dashboard.new_message_from')} ${message.data.user_name || t('dashboard.unknown_user')}`);
    });

    const unsubscribeNewAlert = subscribe('new_alert', (message) => {
      setStats(prev => ({
        ...prev,
        total_alerts: prev.total_alerts + 1
      }));
      addRecentActivity('alert', `${t('dashboard.new_alert')} ${message.data.title}`);
    });

    const unsubscribeLocationUpdate = subscribe('location_update', (message) => {
      addRecentActivity('location', `${message.data.user_name || t('dashboard.unknown_user')} ${t('dashboard.location_updated')}`);
    });

    return () => {
      unsubscribeStats();
      unsubscribeNewMessage();
      unsubscribeNewAlert();
      unsubscribeLocationUpdate();
    };
  }, [subscribe]);

  const fetchStats = async () => {
    try {
      setError(null);
      const [usersRes, messagesRes, alertsRes, zonesRes] = await Promise.all([
        axios.get('/api/users/stats/overview'),
        axios.get('/api/messages/stats/daily'),
        axios.get('/api/alerts/stats/overview'),
        axios.get('/api/zones/stats')
      ]);

      const usersData = usersRes.data;
      const messagesData = messagesRes.data;
      const alertsData = alertsRes.data;
      const zonesData = zonesRes.data;

      setStats({
        total_users: usersData.total_users || 0,
        active_sessions: usersData.active_sessions || 0,
        online_users: usersData.online_users || 0,
        messages_today: messagesData.messages_today || 0,
        bot_status: 'Online', // Assume online for now
        total_alerts: alertsData.total_alerts || 0,
        active_zones: zonesData.active_zones || 0
      });
    } catch (error) {
      console.error('Error fetching stats:', error);
      setError(t('dashboard.failed_load'));
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentActivity = async () => {
    try {
      const response = await axios.get('/api/audit/recent?limit=10');
      setRecentActivity(response.data.activities || []);
    } catch (error) {
      console.error('Error fetching recent activity:', error);
    }
  };

  const addRecentActivity = (type, description) => {
    const newActivity = {
      id: Date.now(),
      type,
      description,
      timestamp: new Date().toISOString()
    };

    setRecentActivity(prev => [newActivity, ...prev.slice(0, 9)]);
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'message': return <MessageSquare className="w-4 h-4" />;
      case 'alert': return <AlertTriangle className="w-4 h-4" />;
      case 'location': return <MapPin className="w-4 h-4" />;
      default: return <Activity className="w-4 h-4" />;
    }
  };

  const getActivityColor = (type) => {
    switch (type) {
      case 'message': return 'text-blue-400';
      case 'alert': return 'text-red-400';
      case 'location': return 'text-green-400';
      default: return 'text-gray-400';
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <SkeletonCard className="h-8 w-48" />
          <SkeletonCard className="h-6 w-24" />
        </div>

        {/* Stats Cards Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }, (_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>

        {/* Secondary Stats Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Array.from({ length: 3 }, (_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>

        {/* Recent Activity Skeleton */}
        <SkeletonCard className="h-96" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <GlassCard className="text-center max-w-md">
          <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">{t('dashboard.error_loading')}</h2>
          <p className="text-gray-300 mb-6">{error}</p>
          <button
            onClick={fetchStats}
            className="px-4 py-2 bg-accent-cyan text-white rounded-lg hover:bg-accent-cyan/80 transition-colors"
          >
            {t('dashboard.try_again')}
          </button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white" id="dashboard-title">{t('dashboard.title')}</h1>
        <div className="flex items-center space-x-2" role="status" aria-live="polite" aria-label="WebSocket connection status">
          <div
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}
            aria-hidden="true"
          ></div>
          <span className="text-sm text-gray-400">
            {isConnected ? t('dashboard.live') : t('dashboard.disconnected')}
          </span>
        </div>
      </header>

      {/* Stats Cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" aria-labelledby="stats-heading">
        <h2 id="stats-heading" className="sr-only">{t('dashboard.system_statistics')}</h2>
        <GlassCard className="text-center" role="region" aria-labelledby="users-stat">
          <Users className="w-8 h-8 text-accent-cyan mx-auto mb-2" aria-hidden="true" />
          <div className="text-2xl font-bold text-white" id="users-stat">{stats.total_users}</div>
          <div className="text-sm text-gray-400">{t('dashboard.total_users')}</div>
          <div className="text-xs text-green-400 mt-1" aria-label={`${stats.online_users} ${t('dashboard.users_online')}`}>{stats.online_users} {t('dashboard.online')}</div>
        </GlassCard>

        <GlassCard className="text-center" role="region" aria-labelledby="sessions-stat">
          <Activity className="w-8 h-8 text-accent-purple mx-auto mb-2" aria-hidden="true" />
          <div className="text-2xl font-bold text-white" id="sessions-stat">{stats.active_sessions}</div>
          <div className="text-sm text-gray-400">{t('dashboard.active_sessions')}</div>
        </GlassCard>

        <GlassCard className="text-center" role="region" aria-labelledby="messages-stat">
          <MessageSquare className="w-8 h-8 text-accent-green mx-auto mb-2" aria-hidden="true" />
          <div className="text-2xl font-bold text-white" id="messages-stat">{stats.messages_today}</div>
          <div className="text-sm text-gray-400">{t('dashboard.messages_today')}</div>
        </GlassCard>

        <GlassCard className="text-center" role="region" aria-labelledby="bot-stat">
          <Bot className="w-8 h-8 text-accent-pink mx-auto mb-2" aria-hidden="true" />
          <div className="text-2xl font-bold text-white" id="bot-stat">{stats.bot_status}</div>
          <div className="text-sm text-gray-400">{t('dashboard.bot_status')}</div>
        </GlassCard>
      </section>

      {/* Secondary Stats */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6" aria-labelledby="secondary-stats-heading">
        <h2 id="secondary-stats-heading" className="sr-only">{t('dashboard.additional_statistics')}</h2>
        <GlassCard className="text-center" role="region" aria-labelledby="alerts-stat">
          <AlertTriangle className="w-6 h-6 text-red-400 mx-auto mb-2" aria-hidden="true" />
          <div className="text-xl font-bold text-white" id="alerts-stat">{stats.total_alerts}</div>
          <div className="text-sm text-gray-400">{t('dashboard.total_alerts')}</div>
        </GlassCard>

        <GlassCard className="text-center" role="region" aria-labelledby="zones-stat">
          <MapPin className="w-6 h-6 text-blue-400 mx-auto mb-2" aria-hidden="true" />
          <div className="text-xl font-bold text-white" id="zones-stat">{stats.active_zones}</div>
          <div className="text-sm text-gray-400">{t('dashboard.active_zones')}</div>
        </GlassCard>

        <GlassCard className="text-center" role="region" aria-labelledby="websocket-stat">
          <Zap className="w-6 h-6 text-yellow-400 mx-auto mb-2" aria-hidden="true" />
          <div className="text-xl font-bold text-white" id="websocket-stat">{isConnected ? t('status.connected') : t('status.disconnected')}</div>
          <div className="text-sm text-gray-400">{t('dashboard.websocket_status')}</div>
        </GlassCard>
      </section>

      {/* Recent Activity */}
      <GlassCard title={t('dashboard.recent_activity')} role="region" aria-labelledby="activity-heading">
        <div
          className="space-y-3 max-h-96 overflow-y-auto"
          role="log"
          aria-live="polite"
          aria-label={t('dashboard.activity_log')}
        >
          {recentActivity.map((activity) => (
            <article
              key={activity.id || activity.timestamp}
              className="flex items-center space-x-3 p-3 bg-dark-800/30 rounded-lg"
              aria-label={`${activity.type} ${t('dashboard.activity_label')} ${activity.description}`}
            >
              <div className={getActivityColor(activity.type)} aria-hidden="true">
                {getActivityIcon(activity.type)}
              </div>
              <div className="flex-1">
                <p className="text-sm text-white">{activity.description}</p>
                <time
                  className="text-xs text-gray-400"
                  dateTime={activity.timestamp}
                >
                  {new Date(activity.timestamp).toLocaleTimeString()}
                </time>
              </div>
            </article>
          ))}
          {recentActivity.length === 0 && (
            <p className="text-gray-400 text-center py-8" role="status">{t('dashboard.no_recent_activity')}</p>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

export default memo(Dashboard);