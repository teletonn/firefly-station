import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from '../ui/GlassCard';

const ProcessMonitor = ({ onStatsUpdate }) => {
  const { t } = useTranslation();
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [filters, setFilters] = useState({
    process_id: '',
    status: ''
  });

  useEffect(() => {
    fetchExecutions();
  }, [filters]);

  const fetchExecutions = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.process_id) params.append('process_id', filters.process_id);
      if (filters.status) params.append('status', filters.status);

      const response = await fetch(`/api/processes/executions/?${params}`);
      const data = await response.json();
      setExecutions(data.executions || []);
    } catch (error) {
      console.error('Error fetching executions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchExecutionDetails = async (executionId) => {
    try {
      const response = await fetch(`/api/processes/executions/${executionId}`);
      const data = await response.json();
      setSelectedExecution(data);
      setShowDetailsModal(true);
    } catch (error) {
      console.error('Error fetching execution details:', error);
    }
  };

  const getStatusBadgeColor = (status) => {
    const colors = {
      running: 'bg-blue-400/20 text-blue-400 border-blue-400/30',
      completed: 'bg-green-400/20 text-green-400 border-green-400/30',
      failed: 'bg-red-400/20 text-red-400 border-red-400/30',
      timeout: 'bg-yellow-400/20 text-yellow-400 border-yellow-400/30'
    };
    return colors[status] || 'bg-gray-400/20 text-gray-400 border-gray-400/30';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (startTime, endTime) => {
    if (!endTime) return t('processMonitor.running_duration');
    const duration = new Date(endTime) - new Date(startTime);
    return `${(duration / 1000).toFixed(2)}s`;
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div>
             <label className="block text-sm font-medium text-gray-300 mb-2">{t('processMonitor.process_id')}</label>
             <input
               type="text"
               value={filters.process_id}
               onChange={(e) => setFilters({ ...filters, process_id: e.target.value })}
               placeholder={t('processMonitor.filter_process')}
               className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
             />
           </div>
           <div>
             <label className="block text-sm font-medium text-gray-300 mb-2">{t('processMonitor.status')}</label>
             <select
               value={filters.status}
               onChange={(e) => setFilters({ ...filters, status: e.target.value })}
               className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
             >
               <option value="">{t('processMonitor.all_statuses')}</option>
               <option value="running">{t('processMonitor.running')}</option>
               <option value="completed">{t('processMonitor.completed')}</option>
               <option value="failed">{t('processMonitor.failed')}</option>
               <option value="timeout">{t('processMonitor.timeout')}</option>
             </select>
           </div>
         </div>
      </GlassCard>

      {/* Executions List */}
      <GlassCard>
        <div className="space-y-3">
          {executions.map((execution) => (
            <div
              key={execution.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors cursor-pointer"
              onClick={() => fetchExecutionDetails(execution.id)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">{execution.process_name}</h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(execution.status)}`}>
                      {execution.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>{t('processMonitor.execution_id')} {execution.id}</span>
                    <span>{t('processMonitor.triggered_by')} {execution.triggered_by_username || execution.triggered_by}</span>
                    <span>{t('processMonitor.started')} {formatTimestamp(execution.started_at)}</span>
                    {execution.completed_at && <span>{t('processMonitor.duration')} {formatDuration(execution.started_at, execution.completed_at)}</span>}
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-400 mt-1">
                    <span>{t('processMonitor.steps')} {execution.steps_completed}/{execution.total_steps || 'N/A'}</span>
                    {execution.execution_time_ms && <span>{t('processMonitor.time')} {(execution.execution_time_ms / 1000).toFixed(2)}s</span>}
                  </div>
                  {execution.error_message && (
                    <div className="mt-2 p-2 bg-red-900/20 border border-red-600 rounded text-xs text-red-400">
                      {t('processMonitor.error')} {execution.error_message}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {executions.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('processMonitor.no_executions')}</p>
          )}
        </div>
      </GlassCard>

      {/* Execution Details Modal */}
      {showDetailsModal && selectedExecution && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('processMonitor.details')}</h2>
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
              {/* Execution Info */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.process')}</label>
                  <p className="text-white">{selectedExecution.process_name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.status_label')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(selectedExecution.status)}`}>
                    {selectedExecution.status.toUpperCase()}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.started_label')}</label>
                  <p className="text-white">{formatTimestamp(selectedExecution.started_at)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.completed')}</label>
                  <p className="text-white">
                    {selectedExecution.completed_at ? formatTimestamp(selectedExecution.completed_at) : t('processMonitor.not_completed')}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.triggered_by_label')}</label>
                  <p className="text-white">{selectedExecution.triggered_by}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.duration_label')}</label>
                  <p className="text-white">{formatDuration(selectedExecution.started_at, selectedExecution.completed_at)}</p>
                </div>
              </div>

              {/* Trigger Event */}
              {selectedExecution.trigger_event && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processMonitor.trigger_event')}</label>
                  <pre className="text-white bg-dark-800/50 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(JSON.parse(selectedExecution.trigger_event), null, 2)}
                  </pre>
                </div>
              )}

              {/* Steps */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">{t('processMonitor.execution_steps')}</label>
                <div className="space-y-2">
                  {selectedExecution.steps && selectedExecution.steps.map((step, index) => (
                    <div key={index} className="p-3 bg-dark-800/30 rounded border border-dark-600">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <span className="font-medium text-white">{t('processMonitor.step')} {index + 1}</span>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusBadgeColor(step.status)}`}>
                              {step.status.toUpperCase()}
                            </span>
                            <span className="text-gray-400 text-sm">{step.action_type}</span>
                          </div>
                          <div className="text-xs text-gray-400">
                            {t('processMonitor.started')}: {formatTimestamp(step.started_at)}
                            {step.completed_at && ` | ${t('processMonitor.completed')}: ${formatTimestamp(step.completed_at)}`}
                            {step.execution_time_ms && ` | ${t('processMonitor.duration')}: ${(step.execution_time_ms / 1000).toFixed(2)}s`}
                          </div>
                          {step.result && (
                            <pre className="text-white bg-dark-900/50 p-2 rounded text-xs mt-2 overflow-x-auto">
                              {JSON.stringify(JSON.parse(step.result), null, 2)}
                            </pre>
                          )}
                          {step.error_message && (
                            <div className="mt-2 p-2 bg-red-900/20 border border-red-600 rounded text-xs text-red-400">
                              {t('processMonitor.error')} {step.error_message}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {(!selectedExecution.steps || selectedExecution.steps.length === 0) && (
                    <p className="text-gray-400 text-center py-4">{t('processMonitor.no_steps')}</p>
                  )}
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default ProcessMonitor;