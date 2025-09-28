import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';
import { Users as UsersIcon, UserPlus, Edit, Trash2, MapPin, Battery, Clock, Wifi } from 'lucide-react';

const Users = () => {
  const { t } = useTranslation();
  const { subscribe, isConnected } = useWebSocket();
  const [users, setUsers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [stats, setStats] = useState({
    total_users: 0,
    active_sessions: 0,
    registered_users: 0
  });
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({
    id: '',
    long_name: '',
    short_name: '',
    nickname: '',
    latitude: '',
    longitude: '',
    altitude: '',
    battery_level: '',
    tracking_enabled: true
  });

  useEffect(() => {
    fetchUsers();
    fetchStats();
    fetchGroups();
  }, []);

  // Subscribe to real-time user updates
  useEffect(() => {
    const unsubscribeUserUpdate = subscribe('user_update', (message) => {
      fetchUsers(); // Refresh user list
    });

    const unsubscribeStatsUpdate = subscribe('statistics_update', (message) => {
      if (message.data.user_stats) {
        setStats(prev => ({
          ...prev,
          ...message.data.user_stats
        }));
      }
    });

    return () => {
      unsubscribeUserUpdate();
      unsubscribeStatsUpdate();
    };
  }, [subscribe]);

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      console.log('DEBUG: fetchUsers token:', token ? token.substring(0, 50) + '...' : 'no token');
      const response = await fetch('/api/users/?limit=100&offset=0', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      console.log('DEBUG: fetchUsers response status:', response.status);
      const data = await response.json();
      setUsers(data.users || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/users/stats/overview', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      const data = await response.json();
      setStats(prev => ({
        ...prev,
        ...data
      }));
    } catch (error) {
      console.error('Error fetching user stats:', error);
    }
  };

  const fetchGroups = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/users/groups/', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      const data = await response.json();
      setGroups(data.groups || []);
    } catch (error) {
      console.error('Error fetching user groups:', error);
    }
  };

  const createUser = async (userData) => {
    try {
      const token = localStorage.getItem('token');
      console.log('DEBUG: createUser token:', token ? token.substring(0, 50) + '...' : 'no token');
      const response = await fetch('/api/users/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(userData),
      });
      console.log('DEBUG: createUser response status:', response.status);
      if (response.ok) {
        fetchUsers();
        fetchStats();
        setShowAddModal(false);
        setUserForm({
          id: '',
          long_name: '',
          short_name: '',
          nickname: '',
          latitude: '',
          longitude: '',
          altitude: '',
          battery_level: '',
          tracking_enabled: true
        });
      } else {
        console.error('Error creating user:', response.statusText);
      }
    } catch (error) {
      console.error('Error creating user:', error);
    }
  };

  const updateUser = async (userId, userData) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(userData),
      });
      if (response.ok) {
        fetchUsers();
        setShowEditModal(false);
        setEditingUser(null);
      } else {
        console.error('Error updating user:', response.statusText);
      }
    } catch (error) {
      console.error('Error updating user:', error);
    }
  };

  const registerUser = async (userId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ registration_status: 'registered' }),
      });
      if (response.ok) {
        // Update the selected user state to reflect the change
        setSelectedUser(prev => ({ ...prev, registration_status: 'registered' }));
        fetchUsers(); // Refresh the user list
        fetchStats(); // Refresh stats
      } else {
        console.error('Error registering user:', response.statusText);
      }
    } catch (error) {
      console.error('Error registering user:', error);
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm(t('users.confirm_delete'))) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      if (response.ok) {
        fetchUsers();
        fetchStats();
      } else {
        console.error('Error deleting user:', response.statusText);
      }
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  };

  const handleAddUser = () => {
    const userData = {
      user: {
        longName: userForm.long_name,
        shortName: userForm.short_name,
      },
      position: {
        latitude: userForm.latitude ? parseFloat(userForm.latitude) : null,
        longitude: userForm.longitude ? parseFloat(userForm.longitude) : null,
        altitude: userForm.altitude ? parseFloat(userForm.altitude) : null,
      },
      deviceMetrics: {
        batteryLevel: userForm.battery_level ? parseInt(userForm.battery_level) : null,
      },
      id: userForm.id,
      nickname: userForm.nickname,
      tracking_enabled: userForm.tracking_enabled,
    };
    createUser(userData);
  };

  const handleEditUser = () => {
    const userData = {
      user: {
        longName: userForm.long_name,
        shortName: userForm.short_name,
      },
      position: {
        latitude: userForm.latitude ? parseFloat(userForm.latitude) : null,
        longitude: userForm.longitude ? parseFloat(userForm.longitude) : null,
        altitude: userForm.altitude ? parseFloat(userForm.altitude) : null,
      },
      deviceMetrics: {
        batteryLevel: userForm.battery_level ? parseInt(userForm.battery_level) : null,
      },
      nickname: userForm.nickname,
      tracking_enabled: userForm.tracking_enabled,
    };
    updateUser(editingUser.id, userData);
  };

  const openEditModal = (user) => {
    setEditingUser(user);
    setUserForm({
      id: user.id,
      long_name: user.long_name || '',
      short_name: user.short_name || '',
      nickname: user.nickname || '',
      latitude: user.latitude || '',
      longitude: user.longitude || '',
      altitude: user.altitude || '',
      battery_level: user.battery_level || '',
      tracking_enabled: user.tracking_enabled !== false,
    });
    setShowEditModal(true);
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return t('time.never');
    return new Date(timestamp).toLocaleString();
  };

  const getDeviceStatusColor = (status) => {
    switch (status) {
      case 'online': return 'text-green-400';
      case 'offline': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getBatteryColor = (level) => {
    if (!level) return 'text-gray-400';
    if (level > 70) return 'text-green-400';
    if (level > 30) return 'text-yellow-400';
    return 'text-red-400';
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
        <h1 className="text-3xl font-bold text-white">{t('users.title')}</h1>
        <div className="flex items-center space-x-4">
          <GlassButton
            onClick={() => setShowAddModal(true)}
            className="flex items-center space-x-2"
          >
            <UserPlus className="w-4 h-4" />
            <span>{t('users.add_user')}</span>
          </GlassButton>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-sm text-gray-400">
              {isConnected ? t('users.live_updates') : t('users.disconnected')}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="text-center">
          <UsersIcon className="w-8 h-8 text-accent-cyan mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.total_users}</div>
          <div className="text-sm text-gray-400">{t('users.total_users')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <Wifi className="w-8 h-8 text-accent-green mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.active_sessions}</div>
          <div className="text-sm text-gray-400">{t('users.active_sessions')}</div>
        </GlassCard>

        <GlassCard className="text-center">
          <UserPlus className="w-8 h-8 text-accent-purple mx-auto mb-2" />
          <div className="text-2xl font-bold text-white">{stats.registered_users}</div>
          <div className="text-sm text-gray-400">{t('users.registered')}</div>
        </GlassCard>
      </div>

      {/* Users List */}
      <GlassCard title={t('users.users')}>
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {users.map((user) => (
            <div
              key={user.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600 hover:border-accent-cyan/30 transition-colors cursor-pointer"
              onClick={() => setSelectedUser(user)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h3 className="font-semibold text-white">
                      {user.long_name || user.short_name || user.nickname || user.id}
                    </h3>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDeviceStatusColor(user.device_status)} bg-current/20`}>
                      {user.device_status?.toUpperCase() || t('users.unknown')}
                    </span>
                    {user.registration_status === 'registered' && (
                      <span className="px-2 py-1 bg-green-600 text-white rounded-full text-xs">
                        {t('users.registered_status')}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-4 text-xs text-gray-400 mb-2">
                    <span>{t('users.id')} {user.id}</span>
                    {user.latitude && user.longitude && (
                      <span className="flex items-center space-x-1">
                        <MapPin className="w-3 h-3" />
                        {user.latitude.toFixed(4)}, {user.longitude.toFixed(4)}
                      </span>
                    )}
                    {user.battery_level && (
                      <span className="flex items-center space-x-1">
                        <Battery className="w-3 h-3" />
                        <span className={getBatteryColor(user.battery_level)}>{user.battery_level}%</span>
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-4 text-xs text-gray-400">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      {t('users.last_seen_label')} {formatTimestamp(user.last_seen)}
                    </span>
                    {user.last_location_update && (
                      <span>{t('users.last_location')} {formatTimestamp(user.last_location_update)}</span>
                    )}
                  </div>
                </div>

                <div className="flex space-x-2">
                  <GlassButton
                    size="sm"
                    variant="secondary"
                    onClick={(e) => {
                      e.stopPropagation();
                      openEditModal(user);
                    }}
                  >
                    <Edit className="w-4 h-4" />
                  </GlassButton>
                  <GlassButton
                    size="sm"
                    variant="danger"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteUser(user.id);
                    }}
                  >
                    <Trash2 className="w-4 h-4" />
                  </GlassButton>
                </div>
              </div>
            </div>
          ))}
          {users.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('users.no_users')}</p>
          )}
        </div>
      </GlassCard>

      {/* User Groups */}
      <GlassCard title={t('users.user_groups')} className="mt-6">
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {groups.map((group) => (
            <div
              key={group.id}
              className="p-4 bg-dark-800/30 rounded-lg border border-dark-600"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-white">{group.name}</h3>
                  <p className="text-sm text-gray-400">{group.description}</p>
                  <p className="text-xs text-gray-500 mt-1">{t('users.users_label')} {group.user_count || 0}</p>
                </div>
              </div>
            </div>
          ))}
          {groups.length === 0 && (
            <p className="text-gray-400 text-center py-8">{t('users.no_groups')}</p>
          )}
        </div>
      </GlassCard>

      {/* User Details Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('users.details')}</h2>
              <button
                onClick={() => setSelectedUser(null)}
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.user_id')}</label>
                  <p className="text-white">{selectedUser.id}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.status')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDeviceStatusColor(selectedUser.device_status)} bg-current/20`}>
                    {selectedUser.device_status?.toUpperCase() || t('users.unknown')}
                  </span>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.long_name')}</label>
                  <p className="text-white">{selectedUser.long_name || t('users.n_a')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.short_name')}</label>
                  <p className="text-white">{selectedUser.short_name || t('users.n_a')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.nickname')}</label>
                  <p className="text-white">{selectedUser.nickname || t('users.n_a')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.registration_status')}</label>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${selectedUser.registration_status === 'registered' ? 'text-green-400 bg-green-400/20' : 'text-yellow-400 bg-yellow-400/20'}`}>
                      {selectedUser.registration_status?.toUpperCase() || t('users.unregistered')}
                    </span>
                    {selectedUser.registration_status !== 'registered' && (
                      <GlassButton
                        size="sm"
                        onClick={() => registerUser(selectedUser.id)}
                      >
                        {t('users.register')}
                      </GlassButton>
                    )}
                  </div>
                </div>
              </div>

              {(selectedUser.latitude || selectedUser.longitude) && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.location')}</label>
                  <p className="text-white">
                    {selectedUser.latitude?.toFixed(6)}, {selectedUser.longitude?.toFixed(6)}
                    {selectedUser.altitude && `, ${t('users.altitude')} ${selectedUser.altitude}m`}
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.battery_level')}</label>
                  <p className={`text-white ${getBatteryColor(selectedUser.battery_level)}`}>
                    {selectedUser.battery_level ? `${selectedUser.battery_level}%` : t('users.n_a')}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.tracking_enabled')}</label>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${selectedUser.tracking_enabled ? 'text-green-400 bg-green-400/20' : 'text-red-400 bg-red-400/20'}`}>
                    {selectedUser.tracking_enabled ? t('users.yes') : t('users.no')}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.last_seen')}</label>
                  <p className="text-white">{formatTimestamp(selectedUser.last_seen)}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.last_location_update')}</label>
                  <p className="text-white">{formatTimestamp(selectedUser.last_location_update)}</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Add User Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('users.add_new_user')}</h2>
              <button
                onClick={() => setShowAddModal(false)}
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.user_id_required')}</label>
                  <input
                    type="text"
                    value={userForm.id}
                    onChange={(e) => setUserForm({...userForm, id: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.nickname')}</label>
                  <input
                    type="text"
                    value={userForm.nickname}
                    onChange={(e) => setUserForm({...userForm, nickname: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.long_name')}</label>
                  <input
                    type="text"
                    value={userForm.long_name}
                    onChange={(e) => setUserForm({...userForm, long_name: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.short_name')}</label>
                  <input
                    type="text"
                    value={userForm.short_name}
                    onChange={(e) => setUserForm({...userForm, short_name: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.latitude')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.latitude}
                    onChange={(e) => setUserForm({...userForm, latitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.longitude')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.longitude}
                    onChange={(e) => setUserForm({...userForm, longitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.altitude_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.altitude}
                    onChange={(e) => setUserForm({...userForm, altitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.battery_level_label')}</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={userForm.battery_level}
                    onChange={(e) => setUserForm({...userForm, battery_level: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="tracking_enabled"
                  checked={userForm.tracking_enabled}
                  onChange={(e) => setUserForm({...userForm, tracking_enabled: e.target.checked})}
                  className="rounded"
                />
                <label htmlFor="tracking_enabled" className="text-sm text-gray-300">{t('users.tracking_enabled_label')}</label>
              </div>
              <div className="flex justify-end space-x-2">
                <GlassButton
                  variant="secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  {t('users.cancel')}
                </GlassButton>
                <GlassButton
                  onClick={handleAddUser}
                  disabled={!userForm.id}
                >
                  {t('users.add_user')}
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditModal && editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <h2 className="text-xl font-bold text-white">{t('users.edit_user')}</h2>
              <button
                onClick={() => setShowEditModal(false)}
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
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.user_id')}</label>
                  <input
                    type="text"
                    value={userForm.id}
                    disabled
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-gray-400 cursor-not-allowed"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.nickname')}</label>
                  <input
                    type="text"
                    value={userForm.nickname}
                    onChange={(e) => setUserForm({...userForm, nickname: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.long_name')}</label>
                  <input
                    type="text"
                    value={userForm.long_name}
                    onChange={(e) => setUserForm({...userForm, long_name: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.short_name')}</label>
                  <input
                    type="text"
                    value={userForm.short_name}
                    onChange={(e) => setUserForm({...userForm, short_name: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.latitude')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.latitude}
                    onChange={(e) => setUserForm({...userForm, latitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.longitude')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.longitude}
                    onChange={(e) => setUserForm({...userForm, longitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.altitude_label')}</label>
                  <input
                    type="number"
                    step="any"
                    value={userForm.altitude}
                    onChange={(e) => setUserForm({...userForm, altitude: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">{t('users.battery_level_label')}</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={userForm.battery_level}
                    onChange={(e) => setUserForm({...userForm, battery_level: e.target.value})}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="tracking_enabled_edit"
                  checked={userForm.tracking_enabled}
                  onChange={(e) => setUserForm({...userForm, tracking_enabled: e.target.checked})}
                  className="rounded"
                />
                <label htmlFor="tracking_enabled_edit" className="text-sm text-gray-300">{t('users.tracking_enabled_label')}</label>
              </div>
              <div className="flex justify-end space-x-2">
                <GlassButton
                  variant="secondary"
                  onClick={() => setShowEditModal(false)}
                >
                  {t('users.cancel')}
                </GlassButton>
                <GlassButton
                  onClick={handleEditUser}
                >
                  {t('users.update_user')}
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default Users;