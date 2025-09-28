import React, { useState, useEffect, useCallback } from 'react';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';
import GlassPanel from './ui/GlassPanel';

const TriggerConfig = () => {
  const [triggers, setTriggers] = useState([]);
  const [responses, setResponses] = useState([]);
  const [zones, setZones] = useState([]);
  const [userGroups, setUserGroups] = useState([]);
  const [selectedTrigger, setSelectedTrigger] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [activeTab, setActiveTab] = useState('triggers'); // 'triggers', 'responses', 'test'

  // Form states
  const [triggerForm, setTriggerForm] = useState({
    name: '',
    description: '',
    trigger_type: 'keyword',
    trigger_config: {},
    conditions: {},
    priority: 0,
    cooldown_seconds: 0
  });

  const [responseForm, setResponseForm] = useState({
    name: '',
    description: '',
    response_type: 'text',
    content: '',
    variables: {},
    language: 'en',
    target_type: 'all',
    target_ids: [],
    channels: ['meshtastic'],
    priority: 0
  });

  const [testForm, setTestForm] = useState({
    message_text: '',
    user_id: '',
    location_data: null,
    timestamp: ''
  });

  // Load data on component mount
  useEffect(() => {
    loadTriggers();
    loadResponses();
    loadZones();
    loadUserGroups();
  }, []);

  const loadTriggers = async () => {
    try {
      const response = await fetch('/api/bot-controls/triggers');
      const data = await response.json();
      setTriggers(data.triggers || []);
    } catch (error) {
      console.error('Error loading triggers:', error);
    }
  };

  const loadResponses = async () => {
    try {
      const response = await fetch('/api/bot-controls/responses');
      const data = await response.json();
      setResponses(data.responses || []);
    } catch (error) {
      console.error('Error loading responses:', error);
    }
  };

  const loadZones = async () => {
    try {
      const response = await fetch('/api/zones');
      const data = await response.json();
      setZones(data.zones || []);
    } catch (error) {
      console.error('Error loading zones:', error);
    }
  };

  const loadUserGroups = async () => {
    try {
      const response = await fetch('/api/users/groups');
      const data = await response.json();
      setUserGroups(data.groups || []);
    } catch (error) {
      console.error('Error loading user groups:', error);
    }
  };

  const handleCreateTrigger = async () => {
    try {
      const response = await fetch('/api/bot-controls/triggers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(triggerForm),
      });

      if (response.ok) {
        await loadTriggers();
        setIsCreating(false);
        resetTriggerForm();
      } else {
        console.error('Error creating trigger');
      }
    } catch (error) {
      console.error('Error creating trigger:', error);
    }
  };

  const handleUpdateTrigger = async (triggerId) => {
    try {
      const response = await fetch(`/api/bot-controls/triggers/${triggerId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(triggerForm),
      });

      if (response.ok) {
        await loadTriggers();
        setSelectedTrigger(null);
        resetTriggerForm();
      } else {
        console.error('Error updating trigger');
      }
    } catch (error) {
      console.error('Error updating trigger:', error);
    }
  };

  const handleDeleteTrigger = async (triggerId) => {
    if (!confirm('Are you sure you want to delete this trigger?')) return;

    try {
      const response = await fetch(`/api/bot-controls/triggers/${triggerId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadTriggers();
      } else {
        console.error('Error deleting trigger');
      }
    } catch (error) {
      console.error('Error deleting trigger:', error);
    }
  };

  const handleTestTrigger = async (triggerId) => {
    try {
      const response = await fetch(`/api/bot-controls/triggers/${triggerId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testForm),
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      console.error('Error testing trigger:', error);
    }
  };

  const resetTriggerForm = () => {
    setTriggerForm({
      name: '',
      description: '',
      trigger_type: 'keyword',
      trigger_config: {},
      conditions: {},
      priority: 0,
      cooldown_seconds: 0
    });
  };

  const handleCreateResponse = async () => {
    try {
      const response = await fetch('/api/bot-controls/responses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(responseForm),
      });

      if (response.ok) {
        await loadResponses();
        setIsCreating(false);
        resetResponseForm();
      } else {
        console.error('Error creating response');
      }
    } catch (error) {
      console.error('Error creating response:', error);
    }
  };

  const handleUpdateResponse = async (responseId) => {
    try {
      const response = await fetch(`/api/bot-controls/responses/${responseId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(responseForm),
      });

      if (response.ok) {
        await loadResponses();
        setSelectedTrigger(null);
        resetResponseForm();
      } else {
        console.error('Error updating response');
      }
    } catch (error) {
      console.error('Error updating response:', error);
    }
  };

  const handleDeleteResponse = async (responseId) => {
    if (!confirm('Are you sure you want to delete this response?')) return;

    try {
      const response = await fetch(`/api/bot-controls/responses/${responseId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadResponses();
      } else {
        console.error('Error deleting response');
      }
    } catch (error) {
      console.error('Error deleting response:', error);
    }
  };

  const resetResponseForm = () => {
    setResponseForm({
      name: '',
      description: '',
      response_type: 'text',
      content: '',
      variables: {},
      language: 'en',
      target_type: 'all',
      target_ids: [],
      channels: ['meshtastic'],
      priority: 0
    });
  };

  const renderTriggerTypeConfig = (triggerType) => {
    switch (triggerType) {
      case 'keyword':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Keywords (one per line)
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                rows={4}
                value={triggerForm.trigger_config.keywords?.join('\n') || ''}
                onChange={(e) => setTriggerForm({
                  ...triggerForm,
                  trigger_config: {
                    ...triggerForm.trigger_config,
                    keywords: e.target.value.split('\n').filter(k => k.trim())
                  }
                })}
                placeholder="help&#10;emergency&#10;status"
              />
            </div>
            <div className="flex items-center space-x-4">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={triggerForm.trigger_config.use_regex || false}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    trigger_config: {
                      ...triggerForm.trigger_config,
                      use_regex: e.target.checked
                    }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-dark-300">Use Regex</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={triggerForm.trigger_config.case_sensitive || false}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    trigger_config: {
                      ...triggerForm.trigger_config,
                      case_sensitive: e.target.checked
                    }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-dark-300">Case Sensitive</span>
              </label>
            </div>
          </div>
        );

      case 'emoji':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Target Emojis
              </label>
              <input
                type="text"
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                value={triggerForm.trigger_config.emojis?.join(' ') || ''}
                onChange={(e) => setTriggerForm({
                  ...triggerForm,
                  trigger_config: {
                    ...triggerForm.trigger_config,
                    emojis: e.target.value.split(' ').filter(e => e.trim())
                  }
                })}
                placeholder="🚨 ⚠️ 🆘 ❗"
              />
            </div>
            <div className="flex items-center">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={triggerForm.trigger_config.require_exact || false}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    trigger_config: {
                      ...triggerForm.trigger_config,
                      require_exact: e.target.checked
                    }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-dark-300">Require Exact Match</span>
              </label>
            </div>
          </div>
        );

      case 'location':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Trigger Zones
              </label>
              <select
                multiple
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                value={triggerForm.trigger_config.zones || []}
                onChange={(e) => setTriggerForm({
                  ...triggerForm,
                  trigger_config: {
                    ...triggerForm.trigger_config,
                    zones: Array.from(e.target.selectedOptions, option => parseInt(option.value))
                  }
                })}
              >
                {zones.map(zone => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name} ({zone.zone_type})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Trigger Action
              </label>
              <select
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                value={triggerForm.trigger_config.action || 'enter'}
                onChange={(e) => setTriggerForm({
                  ...triggerForm,
                  trigger_config: {
                    ...triggerForm.trigger_config,
                    action: e.target.value
                  }
                })}
              >
                <option value="enter">On Zone Entry</option>
                <option value="exit">On Zone Exit</option>
                <option value="inside">While Inside Zone</option>
              </select>
            </div>
          </div>
        );

      case 'time':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Time Ranges (HH:MM format)
              </label>
              <div className="space-y-2">
                {triggerForm.trigger_config.time_ranges?.map((range, index) => (
                  <div key={index} className="flex space-x-2">
                    <input
                      type="time"
                      className="flex-1 bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                      value={range.start || ''}
                      onChange={(e) => {
                        const newRanges = [...triggerForm.trigger_config.time_ranges];
                        newRanges[index] = { ...newRanges[index], start: e.target.value };
                        setTriggerForm({
                          ...triggerForm,
                          trigger_config: {
                            ...triggerForm.trigger_config,
                            time_ranges: newRanges
                          }
                        });
                      }}
                    />
                    <span className="self-center text-dark-400">to</span>
                    <input
                      type="time"
                      className="flex-1 bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                      value={range.end || ''}
                      onChange={(e) => {
                        const newRanges = [...triggerForm.trigger_config.time_ranges];
                        newRanges[index] = { ...newRanges[index], end: e.target.value };
                        setTriggerForm({
                          ...triggerForm,
                          trigger_config: {
                            ...triggerForm.trigger_config,
                            time_ranges: newRanges
                          }
                        });
                      }}
                    />
                  </div>
                ))}
                <GlassButton
                  onClick={() => setTriggerForm({
                    ...triggerForm,
                    trigger_config: {
                      ...triggerForm.trigger_config,
                      time_ranges: [...(triggerForm.trigger_config.time_ranges || []), { start: '', end: '' }]
                    }
                  })}
                  className="text-sm"
                >
                  Add Time Range
                </GlassButton>
              </div>
            </div>
          </div>
        );

      default:
        return <div className="text-dark-400">Configuration options will appear here based on trigger type.</div>;
    }
  };

  const renderResponseTypeConfig = (responseType) => {
    switch (responseType) {
      case 'template':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Template Content
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500 font-mono"
                rows={6}
                value={responseForm.content}
                onChange={(e) => setResponseForm({
                  ...responseForm,
                  content: e.target.value
                })}
                placeholder="Hello {user_name}! Welcome to {zone_name}."
              />
              <div className="text-xs text-dark-400 mt-1">
                Available variables: {'{user_name}'}, {'{zone_name}'}, {'{timestamp}'}, etc.
              </div>
            </div>
          </div>
        );

      case 'dynamic':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Response Prompt Template
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                rows={4}
                value={responseForm.content}
                onChange={(e) => setResponseForm({
                  ...responseForm,
                  content: e.target.value
                })}
                placeholder="Generate a helpful response in {language} for: {message}"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Custom Variables (JSON)
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500 font-mono"
                rows={3}
                value={JSON.stringify(responseForm.variables, null, 2)}
                onChange={(e) => {
                  try {
                    const variables = JSON.parse(e.target.value);
                    setResponseForm({
                      ...responseForm,
                      variables
                    });
                  } catch (error) {
                    // Invalid JSON, keep current value
                  }
                }}
                placeholder='{"custom_var": "value"}'
              />
            </div>
          </div>
        );

      default:
        return (
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-2">
              Static Response Content
            </label>
            <textarea
              className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
              rows={4}
              value={responseForm.content}
              onChange={(e) => setResponseForm({
                ...responseForm,
                content: e.target.value
              })}
              placeholder="Enter your static response here..."
            />
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Trigger Configuration</h1>
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab('triggers')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'triggers'
                ? 'bg-blue-600 text-white'
                : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
            }`}
          >
            Triggers
          </button>
          <button
            onClick={() => setActiveTab('responses')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'responses'
                ? 'bg-blue-600 text-white'
                : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
            }`}
          >
            Responses
          </button>
          <button
            onClick={() => setActiveTab('test')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'test'
                ? 'bg-blue-600 text-white'
                : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
            }`}
          >
            Test
          </button>
        </div>
      </div>

      {activeTab === 'triggers' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Trigger List */}
          <GlassCard className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">Active Triggers</h2>
              <GlassButton
                onClick={() => setIsCreating(true)}
                className="text-sm"
              >
                Create Trigger
              </GlassButton>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {triggers.map(trigger => (
                <div
                  key={trigger.id}
                  className="bg-dark-800 rounded-lg p-4 border border-dark-600 hover:border-dark-500 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-medium text-white">{trigger.name}</h3>
                      <p className="text-sm text-dark-400 mt-1">{trigger.trigger_type}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          trigger.is_active
                            ? 'bg-green-900 text-green-300'
                            : 'bg-red-900 text-red-300'
                        }`}>
                          {trigger.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <span className="text-xs text-dark-400">
                          Priority: {trigger.priority}
                        </span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          setSelectedTrigger(trigger);
                          setTriggerForm(trigger);
                        }}
                        className="text-blue-400 hover:text-blue-300 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteTrigger(trigger.id)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Trigger Configuration */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">
              {isCreating ? 'Create New Trigger' : 'Edit Trigger'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Trigger Name
                </label>
                <input
                  type="text"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                  value={triggerForm.name}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    name: e.target.value
                  })}
                  placeholder="Enter trigger name..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Description
                </label>
                <textarea
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                  rows={2}
                  value={triggerForm.description}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    description: e.target.value
                  })}
                  placeholder="Describe what this trigger does..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Trigger Type
                </label>
                <select
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  value={triggerForm.trigger_type}
                  onChange={(e) => setTriggerForm({
                    ...triggerForm,
                    trigger_type: e.target.value,
                    trigger_config: {} // Reset config when type changes
                  })}
                >
                  <option value="keyword">Keyword</option>
                  <option value="emoji">Emoji</option>
                  <option value="location">Location</option>
                  <option value="time">Time</option>
                  <option value="user_activity">User Activity</option>
                </select>
              </div>

              {renderTriggerTypeConfig(triggerForm.trigger_type)}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Priority
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    value={triggerForm.priority}
                    onChange={(e) => setTriggerForm({
                      ...triggerForm,
                      priority: parseInt(e.target.value) || 0
                    })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Cooldown (seconds)
                  </label>
                  <input
                    type="number"
                    min="0"
                    className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    value={triggerForm.cooldown_seconds}
                    onChange={(e) => setTriggerForm({
                      ...triggerForm,
                      cooldown_seconds: parseInt(e.target.value) || 0
                    })}
                  />
                </div>
              </div>

              <div className="flex space-x-3">
                <GlassButton
                  onClick={isCreating ? handleCreateTrigger : () => handleUpdateTrigger(selectedTrigger?.id)}
                  className="flex-1"
                >
                  {isCreating ? 'Create Trigger' : 'Update Trigger'}
                </GlassButton>
                {!isCreating && (
                  <GlassButton
                    onClick={() => {
                      setSelectedTrigger(null);
                      setIsCreating(false);
                      resetTriggerForm();
                    }}
                    className="bg-dark-700 hover:bg-dark-600"
                  >
                    Cancel
                  </GlassButton>
                )}
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {activeTab === 'responses' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Response List */}
          <GlassCard className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">Bot Responses</h2>
              <GlassButton
                onClick={() => setIsCreating(true)}
                className="text-sm"
              >
                Create Response
              </GlassButton>
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {responses.map(response => (
                <div
                  key={response.id}
                  className="bg-dark-800 rounded-lg p-4 border border-dark-600 hover:border-dark-500 transition-colors"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h3 className="font-medium text-white">{response.name}</h3>
                      <p className="text-sm text-dark-400 mt-1">{response.response_type}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        <span className={`px-2 py-1 rounded text-xs ${
                          response.is_active
                            ? 'bg-green-900 text-green-300'
                            : 'bg-red-900 text-red-300'
                        }`}>
                          {response.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <span className="text-xs text-dark-400">
                          {response.language.toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => {
                          setSelectedTrigger(response);
                          setResponseForm(response);
                        }}
                        className="text-blue-400 hover:text-blue-300 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteResponse(response.id)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Response Configuration */}
          <GlassCard className="p-6">
            <h2 className="text-xl font-semibold text-white mb-4">
              {isCreating ? 'Create New Response' : 'Edit Response'}
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Response Name
                </label>
                <input
                  type="text"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                  value={responseForm.name}
                  onChange={(e) => setResponseForm({
                    ...responseForm,
                    name: e.target.value
                  })}
                  placeholder="Enter response name..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Response Type
                </label>
                <select
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  value={responseForm.response_type}
                  onChange={(e) => setResponseForm({
                    ...responseForm,
                    response_type: e.target.value
                  })}
                >
                  <option value="text">Static Text</option>
                  <option value="template">Template</option>
                  <option value="dynamic">Dynamic (LLM)</option>
                </select>
              </div>

              {renderResponseTypeConfig(responseForm.response_type)}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Language
                  </label>
                  <select
                    className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    value={responseForm.language}
                    onChange={(e) => setResponseForm({
                      ...responseForm,
                      language: e.target.value
                    })}
                  >
                    <option value="en">English</option>
                    <option value="ru">Русский</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">
                    Priority
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    value={responseForm.priority}
                    onChange={(e) => setResponseForm({
                      ...responseForm,
                      priority: parseInt(e.target.value) || 0
                    })}
                  />
                </div>
              </div>

              <div className="flex space-x-3">
                <GlassButton
                  onClick={isCreating ? handleCreateResponse : () => handleUpdateResponse(selectedTrigger?.id)}
                  className="flex-1"
                >
                  {isCreating ? 'Create Response' : 'Update Response'}
                </GlassButton>
                {!isCreating && (
                  <GlassButton
                    onClick={() => {
                      setSelectedTrigger(null);
                      setIsCreating(false);
                      resetResponseForm();
                    }}
                    className="bg-dark-700 hover:bg-dark-600"
                  >
                    Cancel
                  </GlassButton>
                )}
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {activeTab === 'test' && (
        <GlassCard className="p-6">
          <h2 className="text-xl font-semibold text-white mb-4">Test Triggers</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Test Message
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                rows={3}
                value={testForm.message_text}
                onChange={(e) => setTestForm({
                  ...testForm,
                  message_text: e.target.value
                })}
                placeholder="Enter a test message to trigger bot responses..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  User ID (optional)
                </label>
                <input
                  type="text"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500"
                  value={testForm.user_id}
                  onChange={(e) => setTestForm({
                    ...testForm,
                    user_id: e.target.value
                  })}
                  placeholder="Test user ID"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Timestamp (optional)
                </label>
                <input
                  type="datetime-local"
                  className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                  value={testForm.timestamp}
                  onChange={(e) => setTestForm({
                    ...testForm,
                    timestamp: e.target.value
                  })}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Location Data (JSON, optional)
              </label>
              <textarea
                className="w-full bg-dark-800 border border-dark-600 rounded-lg px-3 py-2 text-white placeholder-dark-400 focus:outline-none focus:border-blue-500 font-mono"
                rows={2}
                value={testForm.location_data ? JSON.stringify(testForm.location_data) : ''}
                onChange={(e) => {
                  try {
                    const location_data = JSON.parse(e.target.value);
                    setTestForm({
                      ...testForm,
                      location_data
                    });
                  } catch (error) {
                    // Invalid JSON, keep current value
                  }
                }}
                placeholder='{"latitude": 55.7558, "longitude": 37.6176}'
              />
            </div>

            <GlassButton
              onClick={() => {
                // Test all triggers
                triggers.forEach(trigger => {
                  handleTestTrigger(trigger.id);
                });
              }}
              className="w-full"
            >
              Test All Triggers
            </GlassButton>

            {testResult && (
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-white mb-3">Test Results</h3>
                <div className="bg-dark-800 rounded-lg p-4 border border-dark-600">
                  <pre className="text-sm text-dark-300 whitespace-pre-wrap">
                    {testResult ? JSON.stringify(testResult, null, 2) : 'No test results available'}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </GlassCard>
      )}
    </div>
  );
};

export default TriggerConfig;