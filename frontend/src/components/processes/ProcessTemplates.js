import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import GlassCard from '../ui/GlassCard';
import GlassButton from '../ui/GlassButton';

const ProcessTemplates = ({ onStatsUpdate }) => {
  const { t } = useTranslation();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    process_id: '',
    name: '',
    description: '',
    category: 'emergency'
  });

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
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/processes/templates/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(createForm),
      });

      if (response.ok) {
        alert(t('processTemplates.template_created'));
        setShowCreateModal(false);
        setCreateForm({
          process_id: '',
          name: '',
          description: '',
          category: 'emergency'
        });
        fetchTemplates();
      }
    } catch (error) {
      console.error('Error creating template:', error);
      alert(t('processTemplates.error_creating_template'));
    }
  };

  const handleInstantiateTemplate = async (templateId, customName = '') => {
    try {
      const response = await fetch(`/api/processes/templates/${templateId}/instantiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: customName || `Process from ${templates.find(t => t.id === templateId)?.name}`,
          description: 'Created from template'
        }),
      });

      if (response.ok) {
        alert(t('processTemplates.process_from_template_success'));
        if (onStatsUpdate) onStatsUpdate();
      }
    } catch (error) {
      console.error('Error instantiating template:', error);
      alert(t('processTemplates.error_from_template'));
    }
  };

  const showTemplateDetails = (template) => {
    setSelectedTemplate(template);
    setShowDetailsModal(true);
  };

  const getCategoryColor = (category) => {
    const colors = {
      emergency: 'text-red-400',
      maintenance: 'text-yellow-400',
      communication: 'text-blue-400',
      monitoring: 'text-green-400'
    };
    return colors[category] || 'text-gray-400';
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
        <h2 className="text-2xl font-bold text-white">{t('processTemplates.title')}</h2>
        <GlassButton
          onClick={() => setShowCreateModal(true)}
          variant="primary"
        >
          {t('processTemplates.create_template')}
        </GlassButton>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((template) => (
          <GlassCard key={template.id} className="cursor-pointer hover:border-accent-cyan/30 transition-colors">
            <div onClick={() => showTemplateDetails(template)}>
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-white text-lg">{template.name}</h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(template.category)} bg-current/20`}>
                  {template.category.toUpperCase()}
                </span>
              </div>
              <p className="text-gray-300 text-sm mb-3">{template.description}</p>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>{t('processTemplates.usage')} {template.usage_count}</span>
                <span>{t('processTemplates.by')} {template.created_by_username}</span>
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {t('processTemplates.created')} {formatTimestamp(template.created_at)}
              </div>
            </div>
            <div className="flex space-x-2 mt-4">
              <GlassButton
                onClick={(e) => {
                  e.stopPropagation();
                  const customName = prompt(t('processTemplates.enter_process_name'), `Process from ${template.name}`);
                  if (customName) handleInstantiateTemplate(template.id, customName);
                }}
                variant="primary"
                className="flex-1 text-sm"
              >
                {t('processTemplates.use_template')}
              </GlassButton>
            </div>
          </GlassCard>
        ))}
        {templates.length === 0 && (
          <div className="col-span-full">
            <GlassCard>
              <p className="text-gray-400 text-center py-8">{t('processTemplates.no_templates')}</p>
            </GlassCard>
          </div>
        )}
      </div>

      {/* Create Template Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-lg mx-4">
            <form onSubmit={handleCreateTemplate}>
              <h2 className="text-xl font-bold text-white mb-4">{t('processTemplates.create_process_template')}</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Process ID</label>
                  <input
                    type="number"
                    value={createForm.process_id}
                    onChange={(e) => setCreateForm({ ...createForm, process_id: e.target.value })}
                    placeholder="ID of existing process"
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">{t('processTemplates.template_name')}</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    placeholder={t('processTemplates.template_name_placeholder')}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">{t('processTemplates.description')}</label>
                  <textarea
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    placeholder={t('processTemplates.template_desc_placeholder')}
                    rows={3}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">{t('processTemplates.category')}</label>
                  <select
                    value={createForm.category}
                    onChange={(e) => setCreateForm({ ...createForm, category: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="emergency">{t('processTemplates.emergency')}</option>
                    <option value="maintenance">{t('processTemplates.maintenance')}</option>
                    <option value="communication">{t('processTemplates.communication')}</option>
                    <option value="monitoring">{t('processTemplates.monitoring')}</option>
                  </select>
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <GlassButton type="submit" variant="primary">
                  {t('processTemplates.create_template_btn')}
                </GlassButton>
                <GlassButton
                  type="button"
                  variant="secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  {t('processTemplates.cancel')}
                </GlassButton>
              </div>
            </form>
          </GlassCard>
        </div>
      )}

      {/* Template Details Modal */}
      {showDetailsModal && selectedTemplate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{selectedTemplate.name}</h2>
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processTemplates.category_label')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(selectedTemplate.category)} bg-current/20`}>
                    {selectedTemplate.category.toUpperCase()}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processTemplates.usage_count')}</label>
                  <p className="text-white">{selectedTemplate.usage_count}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processTemplates.created_by')}</label>
                  <p className="text-white">{selectedTemplate.created_by_username}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('processTemplates.created_label')}</label>
                  <p className="text-white">{formatTimestamp(selectedTemplate.created_at)}</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">{t('processTemplates.description_label')}</label>
                <p className="text-white bg-dark-800/50 p-3 rounded">{selectedTemplate.description}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">{t('processTemplates.template_structure')}</label>
                <pre className="text-white bg-dark-800/50 p-3 rounded text-xs overflow-x-auto max-h-96">
                  {JSON.stringify(JSON.parse(selectedTemplate.template_data), null, 2)}
                </pre>
              </div>

              <div className="flex space-x-3 pt-4">
                <GlassButton
                  onClick={() => {
                    const customName = prompt(t('processTemplates.enter_process_name'), `Process from ${selectedTemplate.name}`);
                    if (customName) {
                      handleInstantiateTemplate(selectedTemplate.id, customName);
                      setShowDetailsModal(false);
                    }
                  }}
                  variant="primary"
                >
                  {t('processTemplates.create_process_from')}
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default ProcessTemplates;