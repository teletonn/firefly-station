import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from '../ui/GlassCard';
import GlassButton from '../ui/GlassButton';

const ProcessBuilder = ({ onStatsUpdate }) => {
  const { t } = useTranslation();
  const [process, setProcess] = useState({
    name: '',
    description: '',
    triggers: [],
    actions: []
  });
  const [templates, setTemplates] = useState([]);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/processes/templates/');
      const data = await response.json();
      setTemplates(data.templates || []);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const handleCreateProcess = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/processes/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(process),
      });

      if (response.ok) {
        alert(t('processBuilder.process_created'));
        setProcess({
          name: '',
          description: '',
          triggers: [],
          actions: []
        });
        if (onStatsUpdate) onStatsUpdate();
      }
    } catch (error) {
      console.error('Error creating process:', error);
      alert(t('processBuilder.error_creating'));
    }
  };

  const handleLoadTemplate = async (templateId) => {
    try {
      const response = await fetch(`/api/processes/templates/${templateId}/instantiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: `${t('processBuilder.new_process_from')} ${templates.find(t => t.id === templateId)?.name}`,
          description: t('processBuilder.created_from_template')
        }),
      });

      if (response.ok) {
        alert(t('processBuilder.process_from_template'));
        setShowTemplateModal(false);
        if (onStatsUpdate) onStatsUpdate();
      }
    } catch (error) {
      console.error('Error creating process from template:', error);
      alert(t('processBuilder.error_from_template'));
    }
  };

  const addTrigger = () => {
    setProcess({
      ...process,
      triggers: [...process.triggers, {
        trigger_type: 'manual',
        trigger_config: {},
        conditions: {},
        priority: 0,
        is_active: true
      }]
    });
  };

  const updateTrigger = (index, field, value) => {
    const newTriggers = [...process.triggers];
    newTriggers[index] = { ...newTriggers[index], [field]: value };
    setProcess({ ...process, triggers: newTriggers });
  };

  const removeTrigger = (index) => {
    setProcess({
      ...process,
      triggers: process.triggers.filter((_, i) => i !== index)
    });
  };

  const addAction = () => {
    setProcess({
      ...process,
      actions: [...process.actions, {
        action_type: 'send_message',
        action_config: {},
        conditions: {},
        action_order: process.actions.length + 1,
        timeout_seconds: 30,
        retry_count: 0
      }]
    });
  };

  const updateAction = (index, field, value) => {
    const newActions = [...process.actions];
    newActions[index] = { ...newActions[index], [field]: value };
    setProcess({ ...process, actions: newActions });
  };

  const removeAction = (index) => {
    setProcess({
      ...process,
      actions: process.actions.filter((_, i) => i !== index)
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">{t('processBuilder.title')}</h2>
        <GlassButton
          onClick={() => setShowTemplateModal(true)}
          variant="secondary"
        >
          {t('processBuilder.load_template')}
        </GlassButton>
      </div>

      <form onSubmit={handleCreateProcess}>
        {/* Basic Info */}
        <GlassCard>
          <h3 className="text-lg font-semibold text-white mb-4">{t('processBuilder.process_info')}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.process_name')}</label>
              <input
                type="text"
                value={process.name}
                onChange={(e) => setProcess({ ...process, name: e.target.value })}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.description')}</label>
              <input
                type="text"
                value={process.description}
                onChange={(e) => setProcess({ ...process, description: e.target.value })}
                className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              />
            </div>
          </div>
        </GlassCard>

        {/* Triggers */}
        <GlassCard>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-white">{t('processBuilder.triggers')}</h3>
            <GlassButton type="button" onClick={addTrigger} variant="secondary" className="text-sm">
              {t('processBuilder.add_trigger')}
            </GlassButton>
          </div>
          <div className="space-y-3">
            {process.triggers.map((trigger, index) => (
              <div key={index} className="p-4 bg-dark-800/50 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.trigger_type')}</label>
                    <select
                      value={trigger.trigger_type}
                      onChange={(e) => updateTrigger(index, 'trigger_type', e.target.value)}
                      className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    >
                      <option value="manual">{t('processBuilder.manual')}</option>
                      <option value="zone_entry">{t('processBuilder.zone_entry')}</option>
                      <option value="zone_exit">{t('processBuilder.zone_exit')}</option>
                      <option value="alert_created">{t('processBuilder.alert_created')}</option>
                      <option value="message_received">{t('processBuilder.message_received')}</option>
                      <option value="time_schedule">{t('processBuilder.time_schedule')}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.priority')}</label>
                    <input
                      type="number"
                      value={trigger.priority}
                      onChange={(e) => updateTrigger(index, 'priority', parseInt(e.target.value))}
                      className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      type="button"
                      onClick={() => removeTrigger(index)}
                      className="px-3 py-2 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-500"
                    >
                      {t('processBuilder.remove')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {process.triggers.length === 0 && (
              <p className="text-gray-400 text-center py-4">{t('processBuilder.no_triggers')}</p>
            )}
          </div>
        </GlassCard>

        {/* Actions */}
        <GlassCard>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-white">{t('processBuilder.actions')}</h3>
            <GlassButton type="button" onClick={addAction} variant="secondary" className="text-sm">
              {t('processBuilder.add_action')}
            </GlassButton>
          </div>
          <div className="space-y-3">
            {process.actions.map((action, index) => (
              <div key={index} className="p-4 bg-dark-800/50 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.action_type')}</label>
                    <select
                      value={action.action_type}
                      onChange={(e) => updateAction(index, 'action_type', e.target.value)}
                      className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    >
                      <option value="send_message">{t('processBuilder.send_message')}</option>
                      <option value="create_alert">{t('processBuilder.create_alert')}</option>
                      <option value="update_zone">{t('processBuilder.update_zone')}</option>
                      <option value="trigger_bot">{t('processBuilder.trigger_bot')}</option>
                      <option value="update_group">{t('processBuilder.update_group')}</option>
                      <option value="send_notification">{t('processBuilder.send_notification')}</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.order')}</label>
                    <input
                      type="number"
                      value={action.action_order}
                      onChange={(e) => updateAction(index, 'action_order', parseInt(e.target.value))}
                      className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">{t('processBuilder.timeout_s')}</label>
                    <input
                      type="number"
                      value={action.timeout_seconds}
                      onChange={(e) => updateAction(index, 'timeout_seconds', parseInt(e.target.value))}
                      className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      type="button"
                      onClick={() => removeAction(index)}
                      className="px-3 py-2 bg-red-600 text-white rounded text-sm font-medium hover:bg-red-500"
                    >
                      {t('processBuilder.remove')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {process.actions.length === 0 && (
              <p className="text-gray-400 text-center py-4">{t('processBuilder.no_actions')}</p>
            )}
          </div>
        </GlassCard>

        <div className="flex space-x-3">
          <GlassButton type="submit" variant="primary">
            {t('processBuilder.create_process')}
          </GlassButton>
        </div>
      </form>

      {/* Template Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('processBuilder.load_from_template')}</h2>
              <button
                onClick={() => setShowTemplateModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              {templates.map((template) => (
                <div
                  key={template.id}
                  className="p-4 bg-dark-800/50 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-semibold text-white">{template.name}</h3>
                      <p className="text-gray-300 text-sm">{template.description}</p>
                      <div className="flex items-center space-x-4 text-xs text-gray-400 mt-2">
                        <span>{t('processBuilder.category')}: {template.category}</span>
                        <span>{t('processBuilder.usage')}: {template.usage_count}</span>
                      </div>
                    </div>
                    <GlassButton
                      onClick={() => handleLoadTemplate(template.id)}
                      variant="primary"
                      className="text-sm"
                    >
                      {t('processBuilder.use_template')}
                    </GlassButton>
                  </div>
                </div>
              ))}
              {templates.length === 0 && (
                <p className="text-gray-400 text-center py-8">{t('processBuilder.no_templates')}</p>
              )}
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default ProcessBuilder;