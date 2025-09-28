import React, { useState, useEffect } from 'react';
import GlassCard from './ui/GlassCard';
import GlassButton from './ui/GlassButton';

const UserGroups = () => {
  const [groups, setGroups] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [activeTab, setActiveTab] = useState('groups');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    parent_group_id: ''
  });

  // Fetch groups and users on component mount
  useEffect(() => {
    fetchGroups();
    fetchUsers();
  }, []);

  const fetchGroups = async () => {
    try {
      const response = await fetch('/api/users/groups');
      const data = await response.json();
      setGroups(data.groups || []);
    } catch (error) {
      console.error('Error fetching groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await fetch('/api/users/');
      const data = await response.json();
      setUsers(data.users || []);
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/users/groups', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowCreateModal(false);
        setFormData({ name: '', description: '' });
        fetchGroups();
      }
    } catch (error) {
      console.error('Error creating group:', error);
    }
  };

  const handleEditGroup = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`/api/users/groups/${selectedGroup.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowEditModal(false);
        setSelectedGroup(null);
        setFormData({ name: '', description: '' });
        fetchGroups();
      }
    } catch (error) {
      console.error('Error updating group:', error);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    // For now, we'll just delete without confirmation
    // In a real app, you'd show a proper confirmation dialog
    try {
      const response = await fetch(`/api/users/groups/${groupId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchGroups();
      }
    } catch (error) {
      console.error('Error deleting group:', error);
    }
  };

  const handleAddUserToGroup = async (userId, groupId) => {
    try {
      const response = await fetch(`/api/users/groups/${groupId}/users/${userId}`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchGroups();
      }
    } catch (error) {
      console.error('Error adding user to group:', error);
    }
  };

  const handleRemoveUserFromGroup = async (userId, groupId) => {
    try {
      const response = await fetch(`/api/users/groups/${groupId}/users/${userId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchGroups();
      }
    } catch (error) {
      console.error('Error removing user from group:', error);
    }
  };

  const openEditModal = (group) => {
    setSelectedGroup(group);
    setFormData({
      name: group.name,
      description: group.description || ''
    });
    setShowEditModal(true);
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
      {/* Tabs */}
      <div className="flex space-x-1 bg-dark-800/50 p-1 rounded-lg">
        {[
          { id: 'groups', label: 'Groups' },
          { id: 'hierarchy', label: 'Hierarchy' }
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

      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white">
          {activeTab === 'hierarchy' ? 'Group Hierarchy' : 'User Groups'}
        </h2>
        <GlassButton
          onClick={() => setShowCreateModal(true)}
          variant="primary"
          className="flex items-center space-x-2"
        >
          <span>+</span>
          <span>Create Group</span>
        </GlassButton>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Groups List */}
        <GlassCard title="Groups" icon={<GroupsIcon />}>
          <div className="space-y-3">
            {groups.map((group) => (
              <div
                key={group.id}
                className="p-4 bg-dark-800/50 rounded-lg border border-dark-600 hover:border-accent-cyan/50 transition-colors cursor-pointer"
                onClick={() => setSelectedGroup(group)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-white">{group.name}</h3>
                    <p className="text-sm text-gray-300 mt-1">{group.description}</p>
                    <p className="text-xs text-gray-400 mt-2">
                      Created: {new Date(group.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditModal(group);
                      }}
                      className="text-accent-cyan hover:text-accent-cyan/80 text-sm"
                    >
                      Edit
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteGroup(group.id);
                      }}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
            {groups.length === 0 && (
              <p className="text-gray-400 text-center py-8">No groups created yet</p>
            )}
          </div>
        </GlassCard>

        {/* Group Details */}
        <GlassCard
          title={selectedGroup ? selectedGroup.name : "Select a Group"}
          icon={selectedGroup ? <GroupDetailIcon /> : <SelectIcon />}
        >
          {selectedGroup ? (
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold text-white mb-2">Group Information</h4>
                <p className="text-gray-300">{selectedGroup.description}</p>
              </div>

              <div>
                <h4 className="font-semibold text-white mb-2">Users in Group</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedGroup.users && selectedGroup.users.length > 0 ? (
                    selectedGroup.users.map((user) => (
                      <div
                        key={user.id}
                        className="flex justify-between items-center p-2 bg-dark-800/30 rounded"
                      >
                        <div>
                          <span className="text-white">{user.long_name || user.short_name}</span>
                          <span className="text-gray-400 text-sm ml-2">({user.id})</span>
                        </div>
                        <button
                          onClick={() => handleRemoveUserFromGroup(user.id, selectedGroup.id)}
                          className="text-red-400 hover:text-red-300 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  ) : (
                    <p className="text-gray-400 text-sm">No users in this group</p>
                  )}
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-white mb-2">Add Users</h4>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {users
                    .filter(user =>
                      !selectedGroup.users ||
                      !selectedGroup.users.some(groupUser => groupUser.id === user.id)
                    )
                    .map((user) => (
                      <div
                        key={user.id}
                        className="flex justify-between items-center p-2 bg-dark-800/30 rounded"
                      >
                        <span className="text-gray-300">{user.long_name || user.short_name}</span>
                        <button
                          onClick={() => handleAddUserToGroup(user.id, selectedGroup.id)}
                          className="text-green-400 hover:text-green-300 text-sm"
                        >
                          Add
                        </button>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-gray-400 text-center py-8">
              Select a group to view details and manage users
            </p>
          )}
        </GlassCard>
      </div>

      {/* Hierarchy Tab */}
      {activeTab === 'hierarchy' && (
        <GlassCard title="Group Hierarchy" icon={<HierarchyIcon />}>
          <div className="space-y-4">
            {groups.length > 0 ? (
              <div className="space-y-4">
                {/* Root level groups */}
                {groups.filter(group => !group.parent_group_id).map((rootGroup) => (
                  <div key={rootGroup.id} className="border border-dark-600 rounded-lg p-4">
                    <GroupNode
                      group={rootGroup}
                      groups={groups}
                      users={users}
                      onEdit={openEditModal}
                      onDelete={handleDeleteGroup}
                      onAddUser={handleAddUserToGroup}
                      onRemoveUser={handleRemoveUserFromGroup}
                      level={0}
                    />
                  </div>
                ))}

                {/* Orphaned groups (with missing parents) */}
                {groups.filter(group => group.parent_group_id && !groups.find(g => g.id === group.parent_group_id)).map((orphanedGroup) => (
                  <div key={orphanedGroup.id} className="border border-yellow-600/30 rounded-lg p-4 bg-yellow-900/10">
                    <GroupNode
                      group={orphanedGroup}
                      groups={groups}
                      users={users}
                      onEdit={openEditModal}
                      onDelete={handleDeleteGroup}
                      onAddUser={handleAddUserToGroup}
                      onRemoveUser={handleRemoveUserFromGroup}
                      level={0}
                      isOrphaned={true}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-center py-8">No groups created yet</p>
            )}
          </div>
        </GlassCard>
      )}

      {/* Create Group Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-md mx-4">
            <form onSubmit={handleCreateGroup}>
              <h2 className="text-xl font-bold text-white mb-4">Create New Group</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Group Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Parent Group (optional)
                  </label>
                  <select
                    value={formData.parent_group_id}
                    onChange={(e) => setFormData({ ...formData, parent_group_id: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  >
                    <option value="">No Parent (Root Group)</option>
                    {groups
                      .filter(group => group.id !== selectedGroup?.id) // Prevent self-selection
                      .map((group) => (
                        <option key={group.id} value={group.id}>{group.name}</option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">
                    Select a parent group to create a subgroup
                  </p>
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <GlassButton type="submit" variant="primary">
                  Create Group
                </GlassButton>
                <GlassButton
                  type="button"
                  variant="secondary"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </GlassButton>
              </div>
            </form>
          </GlassCard>
        </div>
      )}

      {/* Edit Group Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <GlassCard className="w-full max-w-md mx-4">
            <form onSubmit={handleEditGroup}>
              <h2 className="text-xl font-bold text-white mb-4">Edit Group</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Group Name
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 bg-dark-800 border border-dark-600 rounded-lg text-white focus:border-accent-cyan focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex space-x-3 mt-6">
                <GlassButton type="submit" variant="primary">
                  Update Group
                </GlassButton>
                <GlassButton
                  type="button"
                  variant="secondary"
                  onClick={() => setShowEditModal(false)}
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

// GroupNode Component for Hierarchy View
const GroupNode = ({
  group,
  groups,
  users,
  onEdit,
  onDelete,
  onAddUser,
  onRemoveUser,
  level = 0,
  isOrphaned = false
}) => {
  const childGroups = groups.filter(g => g.parent_group_id === group.id);
  const usersInGroup = users.filter(user =>
    group.users && group.users.some(groupUser => groupUser.id === user.id)
  );

  return (
    <div className={`${level > 0 ? 'ml-6 border-l border-dark-600 pl-4' : ''}`}>
      <div className="flex items-start justify-between p-3 bg-dark-800/30 rounded">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h4 className="font-semibold text-white">{group.name}</h4>
            {isOrphaned && (
              <span className="px-2 py-1 bg-yellow-600/20 text-yellow-400 text-xs rounded">
                Orphaned
              </span>
            )}
            <span className="text-xs text-gray-400">
              ({usersInGroup.length} users)
            </span>
          </div>
          {group.description && (
            <p className="text-sm text-gray-300 mt-1">{group.description}</p>
          )}
          <div className="flex items-center space-x-4 mt-2 text-xs text-gray-400">
            <span>Created: {new Date(group.created_at).toLocaleDateString()}</span>
            {group.parent_group_id && (
              <span>Parent: {groups.find(g => g.id === group.parent_group_id)?.name || 'Unknown'}</span>
            )}
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={() => onEdit(group)}
            className="text-accent-cyan hover:text-accent-cyan/80 text-sm"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(group.id)}
            className="text-red-400 hover:text-red-300 text-sm"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Child groups */}
      {childGroups.map((childGroup) => (
        <GroupNode
          key={childGroup.id}
          group={childGroup}
          groups={groups}
          users={users}
          onEdit={onEdit}
          onDelete={onDelete}
          onAddUser={onAddUser}
          onRemoveUser={onRemoveUser}
          level={level + 1}
        />
      ))}
    </div>
  );
};

// Icon Components
const GroupsIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
  </svg>
);

const GroupDetailIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const SelectIcon = () => (
  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
  </svg>
);

const HierarchyIcon = () => (
  <svg className="w-6 h-6 text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5a2 2 0 012-2h4a2 2 0 012 2v2H8V5z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 13l-3-3m0 0l-3 3m3-3v6" />
  </svg>
);

export default UserGroups;