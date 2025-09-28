import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';
import {
  Sparkles,
  Play,
  Save,
  Plus,
  Edit3,
  Trash2,
  Copy,
  CheckCircle
} from 'lucide-react';

const BotResponseTemplates = () => {
  const { isConnected } = useWebSocket();
  const [templates, setTemplates] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [templateFunctions, setTemplateFunctions] = useState({});
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [testTrigger, setTestTrigger] = useState({
    type: 'location',
    user_id: '',
    zone_id: '',
    language: 'en'
  });

  // Template form state
  const [templateForm, setTemplateForm] = useState({
    name: '',
    content: '',
    language: 'en',
    template: 'custom'
  });

  useEffect(() => {
    fetchTemplates();
    fetchTemplateFunctions();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch('/api/bot-controls/responses');
      const data = await response.json();
      setTemplates(data.responses || []);
    } catch (error) {
      console.error('Error fetching templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplateFunctions = async () => {
    try {
      const response = await fetch('/api/bot-controls/template-functions');
      const data = await response.json();
      setTemplateFunctions(data);
    } catch (error) {
      console.error('Error fetching template functions:', error);
    }
  };

  const generateSuggestions = async () => {
    try {
      const params = new URLSearchParams({
        trigger_type: testTrigger.type,
        language: testTrigger.language,
        count: '5'
      });

      if (testTrigger.user_id) params.append('user_id', testTrigger.user_id);
      if (testTrigger.zone_id) params.append('zone_id', testTrigger.zone_id);

      const response = await fetch(`/api/bot-controls/response-suggestions?${params}`);
      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('Error generating suggestions:', error);
    }
  };


  const createTemplate = async () => {
    try {
      const response = await fetch('/api/bot-controls/responses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...templateForm,
          response_type: 'template'
        })
      });

      if (response.ok) {
        setShowCreateModal(false);
        setTemplateForm({
          name: '',
          content: '',
          language: 'en',
          template: 'custom'
        });
        fetchTemplates();
      }
    } catch (error) {
      console.error('Error creating template:', error);
    }
  };

  const insertFunction = (funcName) => {
    const functionCall = `{${funcName}()}`;
    setTemplateForm(prev => ({
      ...prev,
      content: prev.content + functionCall
    }));
  };

  const insertSuggestion = (suggestion) => {
    setTemplateForm(prev => ({
      ...prev,
      content: suggestion
    }));
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
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
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Bot Response Templates</h1>
        <div className="flex items-center space-x-4">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
          <span className="text-sm text-gray-400">
            {isConnected ? 'AI Available' : 'Offline Mode'}
          </span>
          <GlassButton onClick={() => setShowCreateModal(true)} variant="primary">
            <Plus className="w-4 h-4 mr-2" />
            New Template
          </GlassButton>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Template Functions */}
        <GlassCard title="Template Functions" className="lg:col-span-1">
          <div className="space-y-3">
            {Object.entries(templateFunctions.descriptions || {}).map(([func, desc]) => (
              <div key={func} className="flex items-center justify-between p-3 bg-dark-800/30 rounded-lg">
                <div>
                  <div className="text-white font-medium">{func}</div>
                  <div className="text-xs text-gray-400">{desc}</div>
                </div>
                <GlassButton
                  size="sm"
                  variant="ghost"
                  onClick={() => insertFunction(func)}
                >
                  <Plus className="w-3 h-3" />
                </GlassButton>
              </div>
            ))}
          </div>
        </GlassCard>

        {/* AI Suggestions */}
        <GlassCard title="AI Suggestions" className="lg:col-span-2">
          <div className="space-y-4">
            {/* Test Trigger Controls */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <select
                value={testTrigger.type}
                onChange={(e) => setTestTrigger(prev => ({ ...prev, type: e.target.value }))}
                className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              >
                <option value="location">Location</option>
                <option value="emergency">Emergency</option>
                <option value="help_request">Help Request</option>
                <option value="battery_low">Battery Low</option>
              </select>

              <input
                type="text"
                placeholder="User ID"
                value={testTrigger.user_id}
                onChange={(e) => setTestTrigger(prev => ({ ...prev, user_id: e.target.value }))}
                className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              />

              <input
                type="text"
                placeholder="Zone ID"
                value={testTrigger.zone_id}
                onChange={(e) => setTestTrigger(prev => ({ ...prev, zone_id: e.target.value }))}
                className="px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
              />

              <GlassButton onClick={generateSuggestions} variant="primary" className="flex items-center">
                <Sparkles className="w-4 h-4 mr-2" />
                Generate
              </GlassButton>
            </div>

            {/* Suggestions List */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {suggestions.map((suggestion, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-dark-800/30 rounded-lg">
                  <div className="flex-1 text-white text-sm">{suggestion}</div>
                  <div className="flex space-x-2">
                    <GlassButton
                      size="sm"
                      variant="ghost"
                      onClick={() => insertSuggestion(suggestion)}
                    >
                      <Edit3 className="w-3 h-3" />
                    </GlassButton>
                    <GlassButton
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(suggestion)}
                    >
                      <Copy className="w-3 h-3" />
                    </GlassButton>
                  </div>
                </div>
              ))}
              {suggestions.length === 0 && (
                <p className="text-gray-400 text-center py-4">No suggestions generated yet</p>
              )}
            </div>
          </div>
        </GlassCard>
      </div>

      {/* Templates List */}
      <GlassCard title="Response Templates">
        <div className="space-y-3">
          {templates.map((template) => (
            <div
              key={template.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">{template.name}</h3>
                    <span className="px-2 py-1 bg-accent-cyan/20 text-accent-cyan rounded-full text-xs">
                      {template.language.toUpperCase()}
                    </span>
                    <span className="px-2 py-1 bg-dark-700 text-gray-300 rounded-full text-xs">
                      {template.template}
                    </span>
                  </div>
                  <p className="text-gray-300 text-sm mb-2 line-clamp-2">{template.content}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>Type: {template.response_type}</span>
                    <span>Priority: {template.priority}</span>
                    <span className="flex items-center">
                      <CheckCircle className="w-3 h-3 mr-1" />
                      {template.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <GlassButton size="sm" variant="ghost">
                    <Edit3 className="w-4 h-4" />
                  </GlassButton>
                  <GlassButton size="sm" variant="ghost">
                    <Play className="w-4 h-4" />
                  </GlassButton>
                  <GlassButton size="sm" variant="ghost">
                    <Trash2 className="w-4 h-4" />
                  </GlassButton>
                </div>
              </div>
            </div>
          ))}
          {templates.length === 0 && (
            <p className="text-gray-400 text-center py-8">No templates created yet</p>
          )}
        </div>
      </GlassCard>

      {/* Create Template Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">Create Response Template</h2>
              <button
                onClick={() => setShowCreateModal(false)}
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
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Template Name
                  </label>
                  <input
                    type="text"
                    value={templateForm.name}
                    onChange={(e) => setTemplateForm(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    placeholder="e.g., Welcome Message"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Language
                  </label>
                  <select
                    value={templateForm.language}
                    onChange={(e) => setTemplateForm(prev => ({ ...prev, language: e.target.value }))}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="en">English</option>
                    <option value="ru">Russian</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Template Content
                </label>
                <textarea
                  value={templateForm.content}
                  onChange={(e) => setTemplateForm(prev => ({ ...prev, content: e.target.value }))}
                  rows={6}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  placeholder="Use {variable} for substitution and {function()} for dynamic content..."
                />
              </div>

              <div className="flex space-x-3 pt-4">
                <GlassButton onClick={createTemplate} variant="primary">
                  <Save className="w-4 h-4 mr-2" />
                  Create Template
                </GlassButton>
                <GlassButton
                  variant="secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default BotResponseTemplates;