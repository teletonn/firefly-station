import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';

const BotControls = () => {
  const { t } = useTranslation();
  const [botStatus, setBotStatus] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'analytics', 'activity', 'settings'

  useEffect(() => {
    loadBotData();
    // Set up polling for real-time updates
    const interval = setInterval(loadBotData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const loadBotData = async () => {
    try {
      setIsLoading(true);

      // Load bot status and analytics
      const [statusRes, analyticsRes] = await Promise.all([
        fetch('/api/bot-controls/status'),
        fetch('/api/bot-controls/analytics/triggers')
      ]);

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setBotStatus(statusData);
      }

      if (analyticsRes.ok) {
        const analyticsData = await analyticsRes.json();
        setAnalytics(analyticsData);
      }

      // Load recent activity
      await loadRecentActivity();

    } catch (error) {
      console.error('Error loading bot data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadRecentActivity = async () => {
    try {
      const response = await fetch('/api/bot-controls/analytics/triggers?limit=20');
      if (response.ok) {
        const data = await response.json();
        setRecentActivity(data.recent_logs || []);
      }
    } catch (error) {
      console.error('Error loading recent activity:', error);
    }
  };

  const handleBotCommand = async (command, parameters = {}) => {
    try {
      const response = await fetch('/api/bot-controls/command', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ command, parameters }),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`${t('botControls.command_executed')} ${result.message}`);
        await loadBotData(); // Refresh data
      } else {
        alert(t('botControls.error_executing_command'));
      }
    } catch (error) {
      console.error('Error executing bot command:', error);
      alert(t('botControls.error_executing_command'));
    }
  };

  const handleRestartBot = async () => {
    // For now, we'll just restart without confirmation
    // In a real app, you'd show a proper confirmation dialog
    try {
      const response = await fetch('/api/bot-controls/restart', {
        method: 'POST',
      });

      if (response.ok) {
        alert(t('botControls.bot_restart_initiated'));
      } else {
        alert(t('botControls.error_restarting_bot'));
      }
    } catch (error) {
      console.error('Error restarting bot:', error);
      alert(t('botControls.error_restarting_bot'));
    }
  };

  const formatUptime = (uptime) => {
    if (!uptime || uptime === 'N/A') return 'N/A';
    return uptime;
  };

  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-white">{t('botControls.title')}</h1>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">{t('botControls.title')}</h1>
        <div className="flex space-x-3">
          <GlassButton
            onClick={() => handleBotCommand('status_check')}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {t('botControls.status_check')}
          </GlassButton>
          <GlassButton
            onClick={handleRestartBot}
            className="bg-yellow-600 hover:bg-yellow-700"
          >
            {t('botControls.restart_bot')}
          </GlassButton>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-1 bg-dark-800 rounded-lg p-1">
        {[
          { id: 'overview', label: t('botControls.overview') },
          { id: 'analytics', label: t('botControls.analytics') },
          { id: 'activity', label: t('botControls.activity') },
          { id: 'settings', label: t('botControls.settings') }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-600 text-white'
                : 'text-dark-300 hover:text-white hover:bg-dark-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bot Status */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.bot_status')}</h2>

            {botStatus && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-dark-300">{t('botControls.status')}:</span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    botStatus.status === 'running'
                      ? 'bg-green-900 text-green-300'
                      : 'bg-red-900 text-red-300'
                  }`}>
                    {botStatus.status || t('botControls.unknown')}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-dark-300">{t('botControls.uptime')}:</span>
                  <span className="text-white">{formatUptime(botStatus.uptime)}</span>
                </div>

                {botStatus.stats && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{t('botControls.total_users')}:</span>
                      <span className="text-white">{botStatus.stats.total_users || 0}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{t('botControls.total_messages')}:</span>
                      <span className="text-white">{botStatus.stats.total_messages || 0}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{t('botControls.active_sessions')}:</span>
                      <span className="text-white">{botStatus.stats.active_sessions || 0}</span>
                    </div>
                  </>
                )}

                {botStatus.trigger_stats && (
                  <>
                    <hr className="border-dark-600" />
                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{t('botControls.active_triggers')}:</span>
                      <span className="text-white">{botStatus.trigger_stats.active_triggers || 0}</span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-dark-300">{t('botControls.active_responses')}:</span>
                      <span className="text-white">{botStatus.trigger_stats.active_responses || 0}</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </GlassCard>

          {/* Quick Actions */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.quick_actions')}</h2>

            <div className="space-y-3">
              <GlassButton
                onClick={() => handleBotCommand('clear_cache')}
                className="w-full justify-start bg-dark-700 hover:bg-dark-600"
              >
                {t('botControls.clear_cache')}
              </GlassButton>

              <GlassButton
                onClick={() => handleBotCommand('reload_config')}
                className="w-full justify-start bg-dark-700 hover:bg-dark-600"
              >
                {t('botControls.reload_config')}
              </GlassButton>

              <GlassButton
                onClick={() => handleBotCommand('test_connectivity')}
                className="w-full justify-start bg-dark-700 hover:bg-dark-600"
              >
                {t('botControls.test_connectivity')}
              </GlassButton>

              <GlassButton
                onClick={() => handleBotCommand('generate_report')}
                className="w-full justify-start bg-dark-700 hover:bg-dark-600"
              >
                {t('botControls.generate_report')}
              </GlassButton>
            </div>
          </GlassCard>

          {/* Recent Activity Preview */}
          <GlassCard className="p-6 lg:col-span-2">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">{t('botControls.recent_activity')}</h2>
              <GlassButton
                onClick={() => setActiveTab('activity')}
                className="text-sm"
              >
                {t('botControls.view_all')}
              </GlassButton>
            </div>

            <div className="space-y-3 max-h-64 overflow-y-auto">
              {recentActivity.slice(0, 5).map((activity, index) => (
                <div key={index} className="flex items-center justify-between py-2 border-b border-dark-700">
                  <div className="flex-1">
                    <div className="text-sm text-white">{activity.trigger_name || 'Unknown Trigger'}</div>
                    <div className="text-xs text-dark-400">
                      {activity.user_name && `${t('botControls.user_label')} ${activity.user_name}`}
                      {activity.execution_time_ms && ` • ${formatDuration(activity.execution_time_ms)}`}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      activity.success
                        ? 'bg-green-900 text-green-300'
                        : 'bg-red-900 text-red-300'
                    }`}>
                      {activity.success ? t('botControls.success') : t('botControls.failed')}
                    </span>
                    <span className="text-xs text-dark-400">
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}

              {recentActivity.length === 0 && (
                <div className="text-center text-dark-400 py-8">
                  {t('botControls.no_recent')}
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Trigger Analytics */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.trigger_performance')}</h2>

            {analytics && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-dark-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-400">{analytics.total_executions || 0}</div>
                    <div className="text-sm text-dark-400">{t('botControls.total_executions')}</div>
                  </div>
                  <div className="bg-dark-800 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-400">{analytics.successful_executions || 0}</div>
                    <div className="text-sm text-dark-400">{t('botControls.successful')}</div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-dark-300">{t('botControls.success_rate')}:</span>
                  <span className="text-white">
                    {analytics.total_executions > 0
                      ? `${((analytics.successful_executions / analytics.total_executions) * 100).toFixed(1)}%`
                      : 'N/A'
                    }
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-dark-300">{t('botControls.avg_execution_time')}:</span>
                  <span className="text-white">{formatDuration(analytics.average_execution_time * 1000)}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-dark-300">{t('botControls.failed_executions')}:</span>
                  <span className="text-red-400">{analytics.failed_executions || 0}</span>
                </div>
              </div>
            )}
          </GlassCard>

          {/* Response Analytics */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.response_performance')}</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-dark-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-purple-400">0</div>
                  <div className="text-sm text-dark-400">{t('botControls.total_deliveries')}</div>
                </div>
                <div className="bg-dark-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold text-green-400">0</div>
                  <div className="text-sm text-dark-400">{t('botControls.successful')}</div>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-dark-300">{t('botControls.avg_delivery_time')}:</span>
                <span className="text-white">N/A</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-dark-300">{t('botControls.failed_deliveries')}:</span>
                <span className="text-red-400">0</span>
              </div>
            </div>
          </GlassCard>

          {/* Performance Chart Placeholder */}
          <GlassCard className="p-6 lg:col-span-2">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.performance_trends')}</h2>
            <div className="bg-dark-800 rounded-lg p-8 text-center">
              <div className="text-dark-400">{t('botControls.charts_placeholder')}</div>
              <div className="text-sm text-dark-500 mt-2">{t('botControls.integration_needed')}</div>
            </div>
          </GlassCard>
        </div>
      )}

      {activeTab === 'activity' && (
        <GlassCard className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-white">{t('botControls.recent_activity')}</h2>
            <div className="flex space-x-2">
              <select className="bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
                <option value="all">{t('botControls.all_activities')}</option>
                <option value="trigger">{t('botControls.triggers')}</option>
                <option value="response">{t('botControls.responses')}</option>
                <option value="error">{t('botControls.errors')}</option>
              </select>
              <GlassButton
                onClick={loadRecentActivity}
                className="text-sm"
              >
                {t('botControls.refresh')}
              </GlassButton>
            </div>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {recentActivity.map((activity, index) => (
              <div key={index} className="bg-dark-800 rounded-lg p-4 border border-dark-600">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-white">
                        {activity.trigger_name || t('botControls.unknown_trigger')}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${
                        activity.success
                          ? 'bg-green-900 text-green-300'
                          : 'bg-red-900 text-red-300'
                      }`}>
                        {activity.success ? t('botControls.success') : t('botControls.failed')}
                      </span>
                    </div>

                    {activity.user_name && (
                      <div className="text-sm text-dark-400 mt-1">
                        {t('botControls.user')} {activity.user_name}
                      </div>
                    )}

                    {activity.message_text && (
                      <div className="text-sm text-dark-400 mt-1 truncate">
                        {t('botControls.message')} {activity.message_text}
                      </div>
                    )}

                    <div className="flex items-center space-x-4 mt-2 text-xs text-dark-500">
                      <span>{t('botControls.execution')} {formatDuration(activity.execution_time_ms)}</span>
                      <span>{new Date(activity.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {recentActivity.length === 0 && (
              <div className="text-center text-dark-400 py-8">
                {t('botControls.no_activity')}
              </div>
            )}
          </div>
        </GlassCard>
      )}

      {activeTab === 'settings' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bot Configuration */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.bot_configuration')}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  {t('botControls.llm_provider')}
                </label>
                <select className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500">
                  <option value="openrouter">{t('botControls.openrouter')}</option>
                  <option value="ollama">{t('botControls.ollama')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  {t('botControls.model')}
                </label>
                <select className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500">
                  <option value="gpt-5-nano">{t('botControls.gpt5_nano')}</option>
                  <option value="gemma3:latest">{t('botControls.gemma3')}</option>
                </select>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-dark-300">{t('botControls.web_search')}</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-dark-300">{t('botControls.tools_enabled')}</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>
          </GlassCard>

          {/* System Settings */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">{t('botControls.system_settings')}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  {t('botControls.default_language')}
                </label>
                <select className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500">
                  <option value="en">{t('botControls.english')}</option>
                  <option value="ru">{t('botControls.russian')}</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  {t('botControls.max_response_length')}
                </label>
                <input
                  type="number"
                  min="50"
                  max="500"
                  defaultValue="200"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  {t('botControls.trigger_cooldown')}
                </label>
                <input
                  type="number"
                  min="0"
                  max="300"
                  defaultValue="30"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-dark-300">{t('botControls.emergency_mode')}</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
                </label>
              </div>
            </div>
          </GlassCard>

          {/* Save Settings */}
          <GlassCard className="p-6 lg:col-span-2">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold text-white">{t('botControls.save_configuration')}</h3>
                <p className="text-sm text-dark-400">{t('botControls.restart_required')}</p>
              </div>
              <GlassButton className="bg-green-600 hover:bg-green-700">
                {t('botControls.save_settings')}
              </GlassButton>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default BotControls;