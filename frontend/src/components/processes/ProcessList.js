import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from '../ui/GlassCard';

const ProcessList = ({ onStatsUpdate }) => {
  const { t } = useTranslation();
  const [processes, setProcesses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    active_only: true,
    template_id: '',
    created_by: ''
  });

  useEffect(() => {
    fetchProcesses();
  }, [filters]);

  const fetchProcesses = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.active_only !== null) params.append('active_only', filters.active_only);
      if (filters.template_id) params.append('template_id', filters.template_id);
      if (filters.created_by) params.append('created_by', filters.created_by);

      const response = await fetch(`/api/processes/?${params}`);
      const data = await response.json();
      setProcesses(data.processes || []);
    } catch (error) {
      console.error('Error fetching processes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteProcess = async (processId) => {
    try {
      const response = await fetch(`/api/processes/${processId}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ trigger_data: { manual: true } })
      });

      if (response.ok) {
         alert(t('processList.executed_successfully'));
         fetchProcesses();
         if (onStatsUpdate) onStatsUpdate();
       }
     } catch (error) {
       console.error('Error executing process:', error);
       alert(t('processList.error_executing'));
     }
  };

  const handleDeactivateProcess = async (processId) => {
    // For now, we'll just deactivate without confirmation
    // In a real app, you'd show a proper confirmation dialog
    try {
      const response = await fetch(`/api/processes/${processId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
         fetchProcesses();
         if (onStatsUpdate) onStatsUpdate();
       }
     } catch (error) {
       console.error('Error deactivating process:', error);
       alert(t('processList.error_deactivating'));
     }
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
      {/* Filters */}
      <GlassCard>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
           <div>
             <label className="block text-sm font-medium text-gray-300 mb-2">{t('processList.status')}</label>
             <select
               value={filters.active_only}
               onChange={(e) => setFilters({ ...filters, active_only: e.target.value === 'true' })}
               className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
             >
               <option value={true}>{t('processList.active_only')}</option>
               <option value={false}>{t('processList.all_processes')}</option>
             </select>
           </div>
           <div>
             <label className="block text-sm font-medium text-gray-300 mb-2">{t('processList.template_id')}</label>
             <input
               type="text"
               value={filters.template_id}
               onChange={(e) => setFilters({ ...filters, template_id: e.target.value })}
               placeholder={t('processList.filter_by_template')}
               className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
             />
           </div>
           <div>
             <label className="block text-sm font-medium text-gray-300 mb-2">{t('processList.created_by')}</label>
             <input
               type="text"
               value={filters.created_by}
               onChange={(e) => setFilters({ ...filters, created_by: e.target.value })}
               placeholder={t('processList.filter_by_creator')}
               className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
             />
           </div>
         </div>
      </GlassCard>

      {/* Processes List */}
      <GlassCard>
        <div className="space-y-3">
          {processes.map((process) => (
            <div
              key={process.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">{process.name}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${process.is_active ? 'bg-green-400/20 text-green-400' : 'bg-red-400/20 text-red-400'}`}>
                      {process.is_active ? t('processList.active') : t('processList.inactive')}
                    </span>
                  </div>
                  <p className="text-gray-300 text-sm mb-2">{process.description}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>{t('processList.executions')} {process.execution_count}</span>
                    <span>{t('processList.success_rate')} {process.success_rate?.toFixed(1) || 0}%</span>
                    <span>{t('processList.created')} {formatTimestamp(process.created_at)}</span>
                    {process.last_executed && <span>{t('processList.last_run')} {formatTimestamp(process.last_executed)}</span>}
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-400 mt-1">
                    <span>{t('processList.by')} {process.created_by_username}</span>
                    {process.template_name && <span>{t('processList.template')} {process.template_name}</span>}
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleExecuteProcess(process.id)}
                    className="px-3 py-1 bg-accent-cyan text-dark-900 rounded text-sm font-medium hover:bg-accent-cyan/80"
                  >
                    {t('processList.execute')}
                  </button>
                  {process.is_active && (
                    <button
                      onClick={() => handleDeactivateProcess(process.id)}
                      className="px-3 py-1 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-500"
                    >
                      {t('processList.deactivate')}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {processes.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('processList.no_processes')}</p>
          )}
        </div>
      </GlassCard>
    </div>
  );
};

export default ProcessList;