import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from './ui/GlassCard';
import ProcessList from './processes/ProcessList';
import ProcessBuilder from './processes/ProcessBuilder';
import ProcessMonitor from './processes/ProcessMonitor';
import ProcessTemplates from './processes/ProcessTemplates';

const Processes = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('list');
  const [stats, setStats] = useState({});

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/processes/analytics/overview');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching process stats:', error);
    }
  };

  const tabs = [
    { id: 'list', label: t('processes.list'), component: ProcessList },
    { id: 'builder', label: t('processes.builder'), component: ProcessBuilder },
    { id: 'monitor', label: t('processes.monitor'), component: ProcessMonitor },
    { id: 'templates', label: t('processes.templates'), component: ProcessTemplates }
  ];

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || ProcessList;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">{t('processes.management')}</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-white">{stats.total_processes || 0}</div>
          <div className="text-sm text-gray-400">{t('processes.total_processes')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-blue-400">{stats.total_executions || 0}</div>
          <div className="text-sm text-gray-400">{t('processes.total_executions')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-green-400">{stats.success_rate?.toFixed(1) || 0}%</div>
          <div className="text-sm text-gray-400">{t('processes.success_rate')}</div>
        </GlassCard>
        <GlassCard className="text-center">
          <div className="text-2xl font-bold text-yellow-400">{stats.recent_executions || 0}</div>
          <div className="text-sm text-gray-400">{t('processes.recent_30d')}</div>
        </GlassCard>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-800/50 p-1 rounded-lg">
        {tabs.map((tab) => (
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

      {/* Active Component */}
      <div className="mt-6">
        <ActiveComponent onStatsUpdate={fetchStats} />
      </div>
    </div>
  );
};

export default Processes;