import React, { useState, useEffect } from 'react';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';

const AlertConfig = () => {
  const [zones, setZones] = useState([]);
  const [groups, setGroups] = useState([]);
  const [alertRules, setAlertRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('rules');
  const [showCreateRuleModal, setShowCreateRuleModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);

  // Form state for alert rules
  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    alert_type: 'zone_entry',
    severity: 'medium',
    zone_id: '',
    conditions: {
      time_restrictions: null,
      max_capacity: '',
      speed_limits: {
        max_speed_mps: ''
      }
    },
    target_groups: [],
    escalation_rules: {
      enabled: false,
      steps: [
        {
          step_number: 1,
          delay_seconds: 300,
          channels: ['websocket'],
          target_groups: [],
          message_template: ''
        }
      ]
    }
  });

  useEffect(() => {
    fetchZones();
    fetchGroups();
    fetchAlertRules();
  }, []);

  const fetchZones = async () => {
    try {
      const response = await fetch('/api/zones/');
      if (!response.ok) {
        throw new Error(`Failed to fetch zones: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setZones(data.zones || []);
      setError(null);
    } catch (error) {
      console.error('Error fetching zones:', error);
      setError('Failed to load zones. Please try again.');
    }
  };

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/users/groups');
      if (!response.ok) {
        throw new Error(`Failed to fetch groups: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setGroups(data.groups || []);
      setError(null);
    } catch (error) {
      console.error('Error fetching groups:', error);
      setError('Failed to load user groups. Please try again.');
    }
  };

  const fetchAlertRules = async () => {
    try {
      const response = await fetch('/api/alerts/rules/');
      if (!response.ok) {
        throw new Error(`Failed to fetch alert rules: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      setAlertRules(data.rules || []);
      setError(null);
    } catch (error) {
      console.error('Error fetching alert rules:', error);
      setError('Failed to load alert rules. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRule = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/alerts/rules/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(ruleForm),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Alert rule created:', data);
        setShowCreateRuleModal(false);
        resetRuleForm();
        fetchAlertRules(); // Refresh the list
        setError(null);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        setError(`Failed to create alert rule: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error creating alert rule:', error);
      setError('Network error while creating alert rule. Please try again.');
    }
  };

  const handleEditRule = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`/api/alerts/rules/${editingRule.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(ruleForm),
      });

      if (response.ok) {
        console.log('Alert rule updated');
        setEditingRule(null);
        resetRuleForm();
        fetchAlertRules(); // Refresh the list
        setError(null);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        setError(`Failed to update alert rule: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error updating alert rule:', error);
      setError('Network error while updating alert rule. Please try again.');
    }
  };

  const handleDeleteRule = async (ruleId) => {
    // In a real app, you'd show a proper confirmation dialog
    if (!window.confirm('Are you sure you want to delete this alert rule?')) {
      return;
    }

    try {
      const response = await fetch(`/api/alerts/rules/${ruleId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        console.log('Alert rule deleted');
        fetchAlertRules(); // Refresh the list
        setError(null);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        setError(`Failed to delete alert rule: ${errorData.detail || response.statusText}`);
      }
    } catch (error) {
      console.error('Error deleting alert rule:', error);
      setError('Network error while deleting alert rule. Please try again.');
    }
  };

  const resetRuleForm = () => {
    setRuleForm({
      name: '',
      description: '',
      alert_type: 'zone_entry',
      severity: 'medium',
      zone_id: '',
      conditions: {
        time_restrictions: null,
        max_capacity: '',
        speed_limits: {
          max_speed_mps: ''
        }
      },
      target_groups: [],
      escalation_rules: {
        enabled: false,
        steps: [
          {
            step_number: 1,
            delay_seconds: 300,
            channels: ['websocket'],
            target_groups: [],
            message_template: ''
          }
        ]
      }
    });
  };

  const openEditModal = (rule) => {
    setEditingRule(rule);
    // Parse JSON fields back to objects
    const parsedRule = {
      ...rule,
      conditions: rule.conditions ? JSON.parse(rule.conditions) : {
        time_restrictions: null,
        max_capacity: '',
        speed_limits: { max_speed_mps: '' }
      },
      target_groups: rule.target_groups ? JSON.parse(rule.target_groups) : [],
      escalation_rules: rule.escalation_rules ? JSON.parse(rule.escalation_rules) : {
        enabled: false,
        steps: [{
          step_number: 1,
          delay_seconds: 300,
          channels: ['websocket'],
          target_groups: [],
          message_template: ''
        }]
      }
    };
    setRuleForm(parsedRule);
  };

  const addEscalationStep = () => {
    const newStep = {
      step_number: ruleForm.escalation_rules.steps.length + 1,
      delay_seconds: 300,
      channels: ['websocket'],
      target_groups: [],
      message_template: ''
    };

    setRuleForm({
      ...ruleForm,
      escalation_rules: {
        ...ruleForm.escalation_rules,
        steps: [...ruleForm.escalation_rules.steps, newStep]
      }
    });
  };

  const updateEscalationStep = (index, field, value) => {
    const updatedSteps = ruleForm.escalation_rules.steps.map((step, i) =>
      i === index ? { ...step, [field]: value } : step
    );

    setRuleForm({
      ...ruleForm,
      escalation_rules: {
        ...ruleForm.escalation_rules,
        steps: updatedSteps
      }
    });
  };

  const removeEscalationStep = (index) => {
    const updatedSteps = ruleForm.escalation_rules.steps.filter((_, i) => i !== index);
    setRuleForm({
      ...ruleForm,
      escalation_rules: {
        ...ruleForm.escalation_rules,
        steps: updatedSteps
      }
    });
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
        <h1 className="text-3xl font-bold text-white">Alert Configuration</h1>
        <GlassButton
          onClick={() => setShowCreateRuleModal(true)}
          variant="primary"
          className="flex items-center space-x-2"
        >
          <span>+</span>
          <span>Create Alert Rule</span>
        </GlassButton>
      </div>

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
                fetchZones();
                fetchGroups();
                fetchAlertRules();
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

      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-800/50 p-1 rounded-lg">
        {[
          { id: 'rules', label: 'Alert Rules' },
          { id: 'escalation', label: 'Escalation Rules' },
          { id: 'notifications', label: 'Notification Settings' }
        ].map((tab) => (
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

      {/* Alert Rules Tab */}
      {activeTab === 'rules' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Rules List */}
          <GlassCard title="Alert Rules" icon={<RulesIcon />}>
            <div className="space-y-3">
              {alertRules.map((rule) => (
                <div
                  key={rule.id}
                  className="p-4 bg-dark-800/50 rounded-lg border border-dark-600"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <h3 className="font-semibold text-white">{rule.name}</h3>
                      <p className="text-sm text-gray-300">{rule.description}</p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => openEditModal(rule)}
                        className="text-accent-cyan hover:text-accent-cyan/80 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span>Type: {rule.alert_type}</span>
                    <span>Severity: {rule.severity}</span>
                    <span>Zone: {zones.find(z => z.id === parseInt(rule.zone_id))?.name || 'All'}</span>
                  </div>
                </div>
              ))}
              {alertRules.length === 0 && (
                <p className="text-gray-400 text-center py-8">No alert rules configured</p>
              )}
            </div>
          </GlassCard>

          {/* Quick Stats */}
          <GlassCard title="Rule Statistics" icon={<StatsIcon />}>
            <div className="space-y-4">
              <div className="flex justify-between">
                <span className="text-gray-300">Total Rules:</span>
                <span className="text-white font-semibold">{alertRules.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Active Rules:</span>
                <span className="text-green-400 font-semibold">
                  {alertRules.filter(r => r.is_active).length}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Rules with Escalation:</span>
                <span className="text-accent-cyan font-semibold">
                  {alertRules.filter(r => {
                    try {
                      const escalation = r.escalation_rules ? JSON.parse(r.escalation_rules) : {};
                      return escalation.enabled;
                    } catch {
                      return false;
                    }
                  }).length}
                </span>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Escalation Rules Tab */}
      {activeTab === 'escalation' && (
        <GlassCard title="Escalation Rule Builder" icon={<EscalationIcon />}>
          <div className="space-y-6">
            <div className="bg-dark-800/30 p-4 rounded-lg">
              <h3 className="text-lg font-semibold text-white mb-4">Default Escalation Template</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-dark-800/50 rounded">
                  <div>
                    <span className="text-white font-medium">Step 1:</span>
                    <span className="text-gray-300 ml-2">Initial Alert (0 min)</span>
                  </div>
                  <span className="text-xs text-gray-400">WebSocket</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-dark-800/50 rounded">
                  <div>
                    <span className="text-white font-medium">Step 2:</span>
                    <span className="text-gray-300 ml-2">Escalate to Supervisors (5 min)</span>
                  </div>
                  <span className="text-xs text-gray-400">Email + WebSocket</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-dark-800/50 rounded">
                  <div>
                    <span className="text-white font-medium">Step 3:</span>
                    <span className="text-gray-300 ml-2">Emergency Response (15 min)</span>
                  </div>
                  <span className="text-xs text-gray-400">SMS + Email + WebSocket</span>
                </div>
              </div>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Notification Settings Tab */}
      {activeTab === 'notifications' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <GlassCard title="Notification Channels" icon={<NotificationIcon />}>
            <div className="space-y-4">
              {[
                { name: 'WebSocket', description: 'Real-time browser notifications', enabled: true },
                { name: 'Email', description: 'Email notifications for escalation', enabled: true },
                { name: 'SMS', description: 'SMS notifications for critical alerts', enabled: false },
                { name: 'Push Notifications', description: 'Mobile push notifications', enabled: false }
              ].map((channel) => (
                <div key={channel.name} className="flex items-center justify-between p-3 bg-dark-800/30 rounded-lg">
                  <div>
                    <h4 className="font-medium text-white">{channel.name}</h4>
                    <p className="text-sm text-gray-300">{channel.description}</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      defaultChecked={channel.enabled}
                    />
                    <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-cyan"></div>
                  </label>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard title="Notification Preferences" icon={<PreferencesIcon />}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Default Notification Sound
                </label>
                <select className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none">
                  <option>Default</option>
                  <option>Chime</option>
                  <option>Bell</option>
                  <option>Alert</option>
                  <option>None</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Auto-dismiss after (seconds)
                </label>
                <input
                  type="number"
                  defaultValue={30}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-white">Desktop Notifications</h4>
                  <p className="text-sm text-gray-300">Show browser notifications</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-dark-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-accent-cyan"></div>
                </label>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Create/Edit Rule Modal */}
      {(showCreateRuleModal || editingRule) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto">
            <form onSubmit={editingRule ? handleEditRule : handleCreateRule}>
              <h2 className="text-xl font-bold text-white mb-4">
                {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Rule Name
                  </label>
                  <input
                    type="text"
                    value={ruleForm.name}
                    onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Alert Type
                  </label>
                  <select
                    value={ruleForm.alert_type}
                    onChange={(e) => setRuleForm({ ...ruleForm, alert_type: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="zone_entry">Zone Entry</option>
                    <option value="zone_exit">Zone Exit</option>
                    <option value="speeding">Speeding</option>
                    <option value="offline">Offline</option>
                    <option value="battery_low">Battery Low</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Severity
                  </label>
                  <select
                    value={ruleForm.severity}
                    onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Zone
                  </label>
                  <select
                    value={ruleForm.zone_id}
                    onChange={(e) => setRuleForm({ ...ruleForm, zone_id: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="">All Zones</option>
                    {zones.map((zone) => (
                      <option key={zone.id} value={zone.id}>{zone.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={ruleForm.description}
                  onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                />
              </div>

              {/* Target Groups */}
              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Target Groups
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {groups.map((group) => (
                    <label key={group.id} className="flex items-center space-x-2 p-2 bg-dark-800/30 rounded">
                      <input
                        type="checkbox"
                        checked={ruleForm.target_groups.includes(group.id)}
                        onChange={(e) => {
                          const updatedGroups = e.target.checked
                            ? [...ruleForm.target_groups, group.id]
                            : ruleForm.target_groups.filter(id => id !== group.id);
                          setRuleForm({ ...ruleForm, target_groups: updatedGroups });
                        }}
                        className="rounded border-dark-600 text-accent-cyan focus:ring-accent-cyan"
                      />
                      <span className="text-white text-sm">{group.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Escalation Rules */}
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">Escalation Rules</h3>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={ruleForm.escalation_rules.enabled}
                      onChange={(e) => setRuleForm({
                        ...ruleForm,
                        escalation_rules: {
                          ...ruleForm.escalation_rules,
                          enabled: e.target.checked
                        }
                      })}
                      className="rounded border-dark-600 text-accent-cyan focus:ring-accent-cyan"
                    />
                    <span className="text-gray-300">Enable Escalation</span>
                  </label>
                </div>

                {ruleForm.escalation_rules.enabled && (
                  <div className="space-y-4">
                    {ruleForm.escalation_rules.steps.map((step, index) => (
                      <div key={index} className="p-4 bg-dark-800/30 rounded-lg border border-dark-600">
                        <div className="flex justify-between items-center mb-3">
                          <h4 className="font-medium text-white">Step {step.step_number}</h4>
                          {index > 0 && (
                            <button
                              type="button"
                              onClick={() => removeEscalationStep(index)}
                              className="text-red-400 hover:text-red-300 text-sm"
                            >
                              Remove
                            </button>
                          )}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Delay (seconds)
                            </label>
                            <input
                              type="number"
                              value={step.delay_seconds}
                              onChange={(e) => updateEscalationStep(index, 'delay_seconds', parseInt(e.target.value))}
                              className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                            />
                          </div>

                          <div>
                            <label className="block text-sm font-medium text-gray-300 mb-2">
                              Notification Channels
                            </label>
                            <div className="space-y-2">
                              {['websocket', 'email', 'sms'].map((channel) => (
                                <label key={channel} className="flex items-center space-x-2">
                                  <input
                                    type="checkbox"
                                    checked={step.channels.includes(channel)}
                                    onChange={(e) => {
                                      const updatedChannels = e.target.checked
                                        ? [...step.channels, channel]
                                        : step.channels.filter(c => c !== channel);
                                      updateEscalationStep(index, 'channels', updatedChannels);
                                    }}
                                    className="rounded border-dark-600 text-accent-cyan focus:ring-accent-cyan"
                                  />
                                  <span className="text-gray-300 text-sm capitalize">{channel}</span>
                                </label>
                              ))}
                            </div>
                          </div>
                        </div>

                        <div className="mt-3">
                          <label className="block text-sm font-medium text-gray-300 mb-2">
                            Custom Message Template
                          </label>
                          <input
                            type="text"
                            value={step.message_template}
                            onChange={(e) => updateEscalationStep(index, 'message_template', e.target.value)}
                            placeholder="Custom escalation message (optional)"
                            className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                          />
                        </div>
                      </div>
                    ))}

                    <GlassButton
                      type="button"
                      onClick={addEscalationStep}
                      variant="secondary"
                      className="w-full"
                    >
                      Add Escalation Step
                    </GlassButton>
                  </div>
                )}
              </div>

              <div className="flex space-x-3 mt-6">
                <GlassButton type="submit" variant="primary">
                  {editingRule ? 'Update Rule' : 'Create Rule'}
                </GlassButton>
                <GlassButton
                  type="button"
                  variant="secondary"
                  onClick={() => {
                    setShowCreateRuleModal(false);
                    setEditingRule(null);
                    resetRuleForm();
                  }}
                >
                  Cancel
                </GlassButton>
              </div>
            </form>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

// Icon Components
const RulesIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const StatsIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

const EscalationIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

const NotificationIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5-5-5h5V12h-5l5-5 5 5h-5v5z" />
  </svg>
);

const PreferencesIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
  </svg>
);

export default AlertConfig;