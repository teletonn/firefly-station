import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MapPin,
  Save,
  X,
  AlertTriangle,
  CheckCircle,
  Info,
  Settings,
  Plus
} from 'lucide-react';
import GlassButton from './ui/GlassButton';
import GlassCard from './ui/GlassCard';
import GlassPanel from './ui/GlassPanel';

const ZoneManager = ({
  className = ''
}) => {
  const { t } = useTranslation();
  const [zones, setZones] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [editingZone, setEditingZone] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    center_latitude: 55.7558,
    center_longitude: 37.6176,
    radius_meters: 100,
    zone_type: 'safe_zone'
  });
  const [formErrors, setFormErrors] = useState({});

  // Fetch zones on component mount
  useEffect(() => {
    fetchZones();
  }, []);

  const fetchZones = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/zones/?limit=100&offset=0', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setZones(data || []);
      }
    } catch (error) {
      console.error('Error fetching zones:', error);
    } finally {
      setLoading(false);
    }
  };

  const createZone = async (zoneData) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/zones/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(zoneData),
      });
      if (response.ok) {
        const newZone = await response.json();
        setZones(prev => [...prev, newZone]);
        return newZone;
      } else {
        console.error('Error creating zone:', response.statusText);
        throw new Error(response.statusText);
      }
    } catch (error) {
      console.error('Error creating zone:', error);
      throw error;
    }
  };

  const updateZone = async (zoneId, zoneData) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/zones/${zoneId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify(zoneData),
      });
      if (response.ok) {
        const updatedZone = await response.json();
        setZones(prev => prev.map(zone =>
          zone.id === zoneId ? updatedZone : zone
        ));
        return updatedZone;
      } else {
        console.error('Error updating zone:', response.statusText);
        throw new Error(response.statusText);
      }
    } catch (error) {
      console.error('Error updating zone:', error);
      throw error;
    }
  };

  const deleteZone = async (zoneId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/zones/${zoneId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      if (response.ok) {
        setZones(prev => prev.filter(zone => zone.id !== zoneId));
        return true;
      } else {
        console.error('Error deleting zone:', response.statusText);
        throw new Error(response.statusText);
      }
    } catch (error) {
      console.error('Error deleting zone:', error);
      throw error;
    }
  };

  const zoneTypes = [
    { value: 'safe_zone', label: t('zones.safe_zone'), color: '#10b981', icon: CheckCircle },
    { value: 'danger_zone', label: t('zones.danger_zone'), color: '#ef4444', icon: AlertTriangle },
    { value: 'poi', label: t('zones.poi'), color: '#f59e0b', icon: MapPin },
    { value: 'restricted', label: t('zones.restricted'), color: '#8b5cf6', icon: Info }
  ];

  // Reset form
  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      center_latitude: 55.7558,
      center_longitude: 37.6176,
      radius_meters: 100,
      zone_type: 'safe_zone'
    });
    setFormErrors({});
    setIsCreating(false);
    setEditingZone(null);
  };

  // Handle form input changes
  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
    // Clear error when user starts typing
    if (formErrors[field]) {
      setFormErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  // Validate form
  const validateForm = () => {
    const errors = {};

    if (!formData.name.trim()) {
      errors.name = t('validation.required');
    }

    if (formData.radius_meters <= 0) {
      errors.radius_meters = t('validation.invalid_number');
    }

    if (formData.center_latitude < -90 || formData.center_latitude > 90) {
      errors.center_latitude = t('validation.latitude_range');
    }

    if (formData.center_longitude < -180 || formData.center_longitude > 180) {
      errors.center_longitude = t('validation.longitude_range');
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      if (editingZone) {
        await updateZone(editingZone.id, formData);
      } else {
        await createZone(formData);
      }
      resetForm();
    } catch (error) {
      console.error('Error saving zone:', error);
    }
  };

  // Start editing a zone
  const startEditing = (zone) => {
    setEditingZone(zone);
    setFormData({
      name: zone.name,
      description: zone.description || '',
      center_latitude: zone.center_latitude,
      center_longitude: zone.center_longitude,
      radius_meters: zone.radius_meters,
      zone_type: zone.zone_type
    });
    setIsCreating(true);
  };

  // Handle zone deletion
  const handleDelete = async (zoneId) => {
    if (window.confirm(t('messages.confirm_delete'))) {
      try {
        await deleteZone(zoneId);
      } catch (error) {
        console.error('Error deleting zone:', error);
      }
    }
  };

  if (loading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="flex items-center justify-center min-h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Zone List */}
      <GlassPanel
        title={t('zones.title')}
        subtitle={`${zones.length} ${t('nav.zones')}`}
        headerActions={
          <GlassButton
            onClick={() => setIsCreating(true)}
            icon={<MapPin className="w-4 h-4" />}
          >
            {t('zones.create')}
          </GlassButton>
        }
      >
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {zones.map((zone) => {
            const zoneType = zoneTypes.find(type => type.value === zone.zone_type);
            const IconComponent = zoneType?.icon || MapPin;

            return (
              <GlassCard
                key={zone.id}
                title={zone.name}
                subtitle={zoneType?.label}
                icon={
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: `${zoneType?.color}20` }}
                  >
                    <IconComponent
                      className="w-4 h-4"
                      style={{ color: zoneType?.color }}
                    />
                  </div>
                }
                actions={
                  <div className="flex space-x-1">
                    <GlassButton
                      size="sm"
                      variant="ghost"
                      onClick={() => startEditing(zone)}
                    >
                      <Settings className="w-3 h-3" />
                    </GlassButton>
                    <GlassButton
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(zone.id)}
                    >
                      <X className="w-3 h-3" />
                    </GlassButton>
                  </div>
                }
              >
                <div className="space-y-2">
                  {zone.description && (
                    <p className="text-sm text-gray-300">{zone.description}</p>
                  )}
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-400">{t('zones.center')}:</span>
                      <div className="text-white font-mono">
                        {zone.center_latitude.toFixed(4)}
                      </div>
                      <div className="text-white font-mono">
                        {zone.center_longitude.toFixed(4)}
                      </div>
                    </div>
                    <div>
                      <span className="text-gray-400">{t('zones.radius')}:</span>
                      <div className="text-white">{zone.radius_meters}m</div>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400">
                    {t('common.create')}: {new Date(zone.created_at).toLocaleDateString()}
                  </div>
                </div>
              </GlassCard>
            );
          })}

          {zones.length === 0 && (
            <div className="col-span-full text-center py-8">
              <MapPin className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <p className="text-gray-400">{t('messages.no_data')}</p>
              <GlassButton
                className="mt-4"
                onClick={() => setIsCreating(true)}
                icon={<Plus className="w-4 h-4" />}
              >
                {t('zones.create')}
              </GlassButton>
            </div>
          )}
        </div>
      </GlassPanel>

      {/* Create/Edit Zone Form */}
      {isCreating && (
        <GlassPanel
          title={editingZone ? t('zones.edit') : t('zones.create')}
          subtitle={editingZone ? `${t('zones.editing')} ${editingZone.name}` : t('zones.create')}
        >
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Zone Name */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('zones.name')} *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className={`w-full px-3 py-2 bg-white/10 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  formErrors.name ? 'border-red-500' : 'border-white/20'
                }`}
                placeholder={t('zones.name')}
              />
              {formErrors.name && (
                <p className="text-red-400 text-sm mt-1">{formErrors.name}</p>
              )}
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('zones.description')}
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                rows={3}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder={t('zones.description')}
              />
            </div>

            {/* Zone Type */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('zones.type')}
              </label>
              <div className="grid grid-cols-2 gap-2">
                {zoneTypes.map((type) => {
                  const IconComponent = type.icon;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => handleInputChange('zone_type', type.value)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        formData.zone_type === type.value
                          ? 'border-blue-500 bg-blue-500/20'
                          : 'border-white/20 bg-white/5 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <IconComponent
                          className="w-4 h-4"
                          style={{ color: type.color }}
                        />
                        <span className="text-sm text-white">{type.label}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Coordinates */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('zones.center')} - {t('zones.latitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.center_latitude}
                  onChange={(e) => handleInputChange('center_latitude', parseFloat(e.target.value))}
                  className={`w-full px-3 py-2 bg-white/10 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    formErrors.center_latitude ? 'border-red-500' : 'border-white/20'
                  }`}
                  placeholder="55.7558"
                />
                {formErrors.center_latitude && (
                  <p className="text-red-400 text-sm mt-1">{formErrors.center_latitude}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {t('zones.longitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  value={formData.center_longitude}
                  onChange={(e) => handleInputChange('center_longitude', parseFloat(e.target.value))}
                  className={`w-full px-3 py-2 bg-white/10 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    formErrors.center_longitude ? 'border-red-500' : 'border-white/20'
                  }`}
                  placeholder="37.6176"
                />
                {formErrors.center_longitude && (
                  <p className="text-red-400 text-sm mt-1">{formErrors.center_longitude}</p>
                )}
              </div>
            </div>

            {/* Radius */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                {t('zones.radius')} {t('zones.meters')} *
              </label>
              <input
                type="number"
                min="1"
                max="100000"
                value={formData.radius_meters}
                onChange={(e) => handleInputChange('radius_meters', parseInt(e.target.value))}
                className={`w-full px-3 py-2 bg-white/10 border rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  formErrors.radius_meters ? 'border-red-500' : 'border-white/20'
                }`}
                placeholder="100"
              />
              {formErrors.radius_meters && (
                <p className="text-red-400 text-sm mt-1">{formErrors.radius_meters}</p>
              )}
            </div>

            {/* Form Actions */}
            <div className="flex justify-end space-x-3 pt-4">
              <GlassButton
                type="button"
                variant="ghost"
                onClick={resetForm}
              >
                {t('common.cancel')}
              </GlassButton>
              <GlassButton
                type="submit"
                variant="primary"
                icon={<Save className="w-4 h-4" />}
              >
                {editingZone ? t('common.update') : t('common.create')}
              </GlassButton>
            </div>
          </form>
        </GlassPanel>
      )}
    </div>
  );
};

export default ZoneManager;