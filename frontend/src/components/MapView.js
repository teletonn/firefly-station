import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../contexts/WebSocketContext';
import { MapContainer, TileLayer, Marker, Popup, Circle, Polyline } from 'react-leaflet';
import L from 'leaflet';
// import 'leaflet.heat'; // Commented out - not available
import { DivIcon } from 'leaflet';
import {
  MapPin,
  Users,
  Edit3,
  Trash2,
  Plus,
  RotateCcw,
  Target,
  Clock,
  Save,
  X
} from 'lucide-react';
import Glassmorphism from './ui/Glassmorphism';
import GlassButton from './ui/GlassButton';
import GlassCard from './ui/GlassCard';
import 'leaflet/dist/leaflet.css';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons for different user types
const createCustomIcon = (color = '#3b82f6', isMoving = false) => {
  return new DivIcon({
    html: `
      <div style="
        width: 12px;
        height: 12px;
        background-color: ${color};
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        ${isMoving ? 'animation: pulse 1.5s infinite;' : ''}
      "></div>
      <style>
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      </style>
    `,
    className: 'custom-marker',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
};

// Zone style configurations
const zoneStyles = {
  safe_zone: {
    color: '#10b981',
    fillColor: '#10b981',
    fillOpacity: 0.2,
    weight: 2
  },
  danger_zone: {
    color: '#ef4444',
    fillColor: '#ef4444',
    fillOpacity: 0.3,
    weight: 3
  },
  poi: {
    color: '#f59e0b',
    fillColor: '#f59e0b',
    fillOpacity: 0.25,
    weight: 2
  },
  restricted: {
    color: '#8b5cf6',
    fillColor: '#8b5cf6',
    fillOpacity: 0.2,
    weight: 2
  }
};

// Map Controls Component
const MapControls = ({
  onDrawMode,
  onEditMode,
  onDeleteMode,
  isDrawing,
  isEditing,
  showHeatmap,
  onToggleHeatmap,
  showDwellTimes,
  onToggleDwellTimes
}) => {
  const { t } = useTranslation();

  return (
    <Glassmorphism className="absolute top-4 right-4 z-[1000] p-2" hover={false}>
      <div className="flex flex-col space-y-2">
        <GlassButton
          variant={isDrawing ? 'primary' : 'ghost'}
          size="sm"
          onClick={onDrawMode}
          icon={<Plus className="w-4 h-4" />}
        >
          {t('map.draw_zone')}
        </GlassButton>
        <GlassButton
          variant={isEditing ? 'primary' : 'ghost'}
          size="sm"
          onClick={onEditMode}
          icon={<Edit3 className="w-4 h-4" />}
        >
          {t('map.edit_zone')}
        </GlassButton>
        <GlassButton
          variant="ghost"
          size="sm"
          onClick={onDeleteMode}
          icon={<Trash2 className="w-4 h-4" />}
        >
          {t('map.delete_zone')}
        </GlassButton>
        <div className="border-t border-gray-600 my-2"></div>
        <GlassButton
          variant={showHeatmap ? 'primary' : 'ghost'}
          size="sm"
          onClick={onToggleHeatmap}
          icon={<MapPin className="w-4 h-4" />}
        >
          {t('map.heatmap')}
        </GlassButton>
        <GlassButton
          variant={showDwellTimes ? 'primary' : 'ghost'}
          size="sm"
          onClick={onToggleDwellTimes}
          icon={<Clock className="w-4 h-4" />}
        >
          {t('map.dwell_times')}
        </GlassButton>
      </div>
    </Glassmorphism>
  );
};

// Zone Info Panel Component
const ZoneInfoPanel = ({ zone, onClose, onEdit, onDelete, isEditing, onSave, onCancel }) => {
  const { t } = useTranslation();
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    center_latitude: 0,
    center_longitude: 0,
    radius_meters: 100,
    zone_type: 'safe_zone'
  });

  // Initialize edit form when zone changes
  useEffect(() => {
    if (zone) {
      setEditForm({
        name: zone.name || '',
        description: zone.description || '',
        center_latitude: zone.center_latitude || 0,
        center_longitude: zone.center_longitude || 0,
        radius_meters: zone.radius_meters || 100,
        zone_type: zone.zone_type || 'safe_zone'
      });
    }
  }, [zone]);

  const handleSave = () => {
    if (onSave) {
      onSave(zone.id, editForm);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  if (!zone) return null;

  if (isEditing) {
    return (
      <Glassmorphism className="absolute top-4 left-4 z-[1000] w-80">
        <GlassCard
          title={t('zones.edit')}
          subtitle={zone.name}
          actions={
            <div className="flex space-x-2">
              <GlassButton size="sm" variant="primary" onClick={handleSave}>
                <Save className="w-4 h-4" />
              </GlassButton>
              <GlassButton size="sm" variant="ghost" onClick={handleCancel}>
                <X className="w-4 h-4" />
              </GlassButton>
            </div>
          }
        >
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {t('zones.name')}
              </label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {t('zones.description')}
              </label>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
                rows={2}
                className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  {t('zones.latitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  value={editForm.center_latitude}
                  onChange={(e) => setEditForm(prev => ({ ...prev, center_latitude: parseFloat(e.target.value) }))}
                  className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  {t('zones.longitude')}
                </label>
                <input
                  type="number"
                  step="any"
                  value={editForm.center_longitude}
                  onChange={(e) => setEditForm(prev => ({ ...prev, center_longitude: parseFloat(e.target.value) }))}
                  className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                {t('zones.radius')} (m)
              </label>
              <input
                type="number"
                min="1"
                value={editForm.radius_meters}
                onChange={(e) => setEditForm(prev => ({ ...prev, radius_meters: parseInt(e.target.value) }))}
                className="w-full px-2 py-1 bg-white/10 border border-white/20 rounded text-white text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        </GlassCard>
      </Glassmorphism>
    );
  }

  return (
    <Glassmorphism className="absolute top-4 left-4 z-[1000] w-80">
      <GlassCard
        title={zone.name}
        subtitle={`${t('zones.type')}: ${t(`zones.${zone.zone_type}`)}`}
        actions={
          <div className="flex space-x-2">
            <GlassButton size="sm" variant="ghost" onClick={onEdit}>
              <Edit3 className="w-4 h-4" />
            </GlassButton>
            <GlassButton size="sm" variant="ghost" onClick={onDelete}>
              <Trash2 className="w-4 h-4" />
            </GlassButton>
            <GlassButton size="sm" variant="ghost" onClick={onClose}>
              <RotateCcw className="w-4 h-4" />
            </GlassButton>
          </div>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-gray-300">{zone.description}</p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-400">{t('zones.center')}:</span>
              <div className="text-white">
                {zone.center_latitude.toFixed(6)}, {zone.center_longitude.toFixed(6)}
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
    </Glassmorphism>
  );
};

// User Marker Component
const UserMarker = ({ user, onClick }) => {
  const { t } = useTranslation();
  const position = [user.latitude, user.longitude];
  const isMoving = user.is_moving || false;
  const lastUpdate = new Date(user.last_location_update);
  const timeAgo = Math.floor((Date.now() - lastUpdate) / 60000); // minutes

  return (
    <Marker
      position={position}
      icon={createCustomIcon(
        user.current_zone_id ? zoneStyles[user.zone_type]?.color || '#3b82f6' : '#6b7280',
        isMoving
      )}
      eventHandlers={{
        click: () => onClick && onClick(user)
      }}
    >
      <Popup>
        <div className="p-2">
          <h3 className="font-semibold text-gray-900">{user.long_name || user.short_name}</h3>
          <p className="text-sm text-gray-600">
            {t('users.last_seen')}: {timeAgo} {t('time.minutes_ago')}
          </p>
          <p className="text-sm text-gray-600">
            {t('users.status')}: {user.device_status === 'online' ? t('users.online') : t('users.offline')}
          </p>
          {user.battery_level && (
            <p className="text-sm text-gray-600">
              {t('users.battery')}: {user.battery_level}%
            </p>
          )}
          {user.current_zone_id && (
            <p className="text-sm text-blue-600">
              Zone: {user.current_zone_name}
            </p>
          )}
        </div>
      </Popup>
    </Marker>
  );
};

// Movement Trail Component
const MovementTrail = ({ trail, color = '#3b82f6' }) => {
  if (!trail || trail.length < 2) return null;

  const positions = trail.map(point => [point.latitude, point.longitude]);

  return (
    <Polyline
      positions={positions}
      pathOptions={{
        color,
        weight: 2,
        opacity: 0.6,
        dashArray: '5, 5'
      }}
    />
  );
};

// Heatmap Layer Component - Commented out due to missing leaflet.heat dependency
// const HeatmapLayer = ({ data, map }) => {
//   useEffect(() => {
//     if (!map || !data || data.length === 0) return;

//     // Create heatmap data format for leaflet.heat
//     const heatData = data.map(point => [
//       point.lat,
//       point.lon,
//       point.intensity / 10 // Normalize intensity
//     ]);

//     // Add heatmap layer
//     const heatLayer = L.heatLayer(heatData, {
//       radius: 25,
//       blur: 15,
//       maxZoom: 10,
//       max: 1.0,
//       gradient: {
//         0.2: 'blue',
//         0.4: 'lime',
//         0.6: 'yellow',
//         0.8: 'orange',
//         1.0: 'red'
//       }
//     }).addTo(map);

//     return () => {
//       if (map.hasLayer(heatLayer)) {
//         map.removeLayer(heatLayer);
//       }
//     };
//   }, [data, map]);

//   return null;
// };

// Dwell Time Overlay Component
const DwellTimeOverlay = ({ dwellTimes }) => {
  if (!dwellTimes || dwellTimes.length === 0) return null;

  return (
    <>
      {dwellTimes.map((zone, index) => (
        <Circle
          key={`dwell-${index}`}
          center={[zone.center_lat || 0, zone.center_lon || 0]}
          radius={50} // Small indicator circle
          pathOptions={{
            color: '#ff6b6b',
            fillColor: '#ff6b6b',
            fillOpacity: 0.8,
            weight: 2
          }}
        >
          <Popup>
            <div className="p-2">
              <h3 className="font-semibold text-gray-900">{zone.zone_name}</h3>
              <p className="text-sm text-gray-600">
                Users: {zone.users}<br/>
                Avg Dwell: {zone.avg_dwell_hours.toFixed(1)} hours
              </p>
            </div>
          </Popup>
        </Circle>
      ))}
    </>
  );
};

// Main Map Component
const MapView = ({
  className = '',
  center = [55.7558, 37.6176],
  zoom = 13,
  users = [],
  zones = [],
  trails = [],
  onUserClick
}) => {
  const { t } = useTranslation();
  const { subscribe, isConnected } = useWebSocket();
  const mapRef = useRef();
  const [selectedZone, setSelectedZone] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [liveUsers, setLiveUsers] = useState([]);
  const [liveZones, setLiveZones] = useState([]);
  const [movementTrails, setMovementTrails] = useState([]);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [dwellTimes, setDwellTimes] = useState([]);
  const [showDwellTimes, setShowDwellTimes] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isEditingZone, setIsEditingZone] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch initial data
  useEffect(() => {
    fetchZones();
    fetchUsers();
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
        setLiveZones(data || []);
      }
    } catch (error) {
      console.error('Error fetching zones:', error);
    }
  };

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/users/?limit=100&offset=0', {
        headers: {
          'Authorization': token ? `Bearer ${token}` : '',
        },
      });
      if (response.ok) {
        const data = await response.json();
        setLiveUsers(data.users || []);
      }
    } catch (error) {
      console.error('Error fetching users:', error);
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
        setLiveZones(prev => [...prev, newZone]);
        return newZone;
      } else {
        console.error('Error creating zone:', response.statusText);
      }
    } catch (error) {
      console.error('Error creating zone:', error);
    }
    return null;
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
        setLiveZones(prev => prev.map(zone =>
          zone.id === zoneId ? updatedZone : zone
        ));
        return updatedZone;
      } else {
        console.error('Error updating zone:', response.statusText);
      }
    } catch (error) {
      console.error('Error updating zone:', error);
    }
    return null;
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
        setLiveZones(prev => prev.filter(zone => zone.id !== zoneId));
        return true;
      } else {
        console.error('Error deleting zone:', response.statusText);
      }
    } catch (error) {
      console.error('Error deleting zone:', error);
    }
    return false;
  };

  // Handle zone click
  const handleZoneClick = (zone) => {
    setSelectedZone(zone);
  };

  // Initialize live data
  useEffect(() => {
    setLiveUsers(users);
    setLiveZones(zones);
    setMovementTrails(trails);
  }, [users, zones, trails]);


  const fetchDwellTimes = async () => {
    try {
      const response = await fetch('/api/geolocation/analytics/dwell-time?days=7');
      const data = await response.json();
      setDwellTimes(data.dwell_times || []);
    } catch (error) {
      console.error('Error fetching dwell times:', error);
    }
  };


  useEffect(() => {
    if (showDwellTimes) {
      fetchDwellTimes();
    }
  }, [showDwellTimes]);

  // Subscribe to real-time updates
  useEffect(() => {
    const unsubscribeLocationUpdate = subscribe('location_update', (message) => {
      const locationData = message.data;
      setLiveUsers(prev => prev.map(user =>
        user.id === locationData.user_id
          ? {
              ...user,
              latitude: locationData.latitude,
              longitude: locationData.longitude,
              altitude: locationData.altitude,
              last_location_update: locationData.timestamp,
              is_moving: true // Assume moving if location updated
            }
          : user
      ));

      // Add to movement trail
      setMovementTrails(prev => {
        const userTrail = prev.find(trail => trail.user_id === locationData.user_id);
        if (userTrail) {
          userTrail.points.push({
            latitude: locationData.latitude,
            longitude: locationData.longitude,
            timestamp: locationData.timestamp
          });
          // Keep only last 50 points
          if (userTrail.points.length > 50) {
            userTrail.points = userTrail.points.slice(-50);
          }
        } else {
          prev.push({
            user_id: locationData.user_id,
            color: '#3b82f6',
            points: [{
              latitude: locationData.latitude,
              longitude: locationData.longitude,
              timestamp: locationData.timestamp
            }]
          });
        }
        return [...prev];
      });
    });

    const unsubscribeZoneChange = subscribe('zone_change', (message) => {
      const zoneChangeData = message.data;
      setLiveUsers(prev => prev.map(user =>
        user.id === zoneChangeData.user_id
          ? {
              ...user,
              current_zone_id: zoneChangeData.new_zone_id,
              current_zone_name: zoneChangeData.new_zone_name
            }
          : user
      ));
    });

    const unsubscribeZoneUpdate = subscribe('zone_update', (message) => {
      const zoneData = message.data;
      if (zoneData.action === 'create') {
        setLiveZones(prev => [...prev, zoneData.zone]);
      } else if (zoneData.action === 'update') {
        setLiveZones(prev => prev.map(zone =>
          zone.id === zoneData.zone.id ? zoneData.zone : zone
        ));
      } else if (zoneData.action === 'delete') {
        setLiveZones(prev => prev.filter(zone => zone.id !== zoneData.zone_id));
      }
    });

    return () => {
      unsubscribeLocationUpdate();
      unsubscribeZoneChange();
      unsubscribeZoneUpdate();
    };
  }, [subscribe]);

  // Handle zone edit
  const handleZoneEdit = async (zone) => {
    // For now, just show an alert. In a full implementation, this would open an edit modal
    alert(`Edit zone ${zone.name} - Feature not implemented in map view. Use Zones page.`);
    setSelectedZone(null);
  };

  // Handle zone delete
  const handleZoneDelete = async (zone) => {
    if (window.confirm(`Delete zone "${zone.name}"?`)) {
      await deleteZone(zone.id);
    }
    setSelectedZone(null);
  };

  // Handle zone edit save
  const handleZoneEditSave = async (zoneId, formData) => {
    await updateZone(zoneId, formData);
    setIsEditingZone(false);
    setSelectedZone(null);
  };

  // Handle zone edit cancel
  const handleZoneEditCancel = () => {
    setIsEditingZone(false);
    setSelectedZone(null);
  };

  // Map event handlers
  const handleMapClick = async (e) => {
    if (e.originalEvent.ctrlKey) {
      // CTRL+click: Create new zone at clicked location
      const newZone = {
        name: `Zone ${liveZones.length + 1}`,
        center_latitude: e.latlng.lat,
        center_longitude: e.latlng.lng,
        radius_meters: 100,
        zone_type: 'safe_zone'
      };
      console.log('Creating new zone via CTRL+click:', newZone);
      await createZone(newZone);
    } else if (isDrawing) {
      // Create new zone at clicked location (legacy drawing mode)
      const newZone = {
        name: `Zone ${liveZones.length + 1}`,
        center_latitude: e.latlng.lat,
        center_longitude: e.latlng.lng,
        radius_meters: 100,
        zone_type: 'safe_zone'
      };
      console.log('Creating new zone:', newZone);
      await createZone(newZone);
      setIsDrawing(false);
    }
  };

  return (
    <div className={`relative w-full h-full ${className}`}>
      <MapContainer
        center={center}
        zoom={zoom}
        className="w-full h-full z-0"
        ref={(map) => {
          mapRef.current = map;
        }}
        onClick={handleMapClick}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {/* Render zones */}
        {liveZones.map((zone) => (
          <Circle
            key={zone.id}
            center={[zone.center_latitude, zone.center_longitude]}
            radius={zone.radius_meters}
            pathOptions={zoneStyles[zone.zone_type] || zoneStyles.safe_zone}
            eventHandlers={{
              click: (e) => {
                e.originalEvent.stopPropagation();
                if (e.originalEvent.ctrlKey) {
                  // CTRL+click: Edit zone
                  setSelectedZone(zone);
                  setIsEditingZone(true);
                  setIsDrawing(false);
                  setIsEditing(false);
                  setIsDeleting(false);
                } else if (isDeleting) {
                  handleZoneDelete(zone);
                } else {
                  handleZoneClick(zone);
                }
              }
            }}
          >
            <Popup>
              <div className="p-2">
                <h3 className="font-semibold">{zone.name}</h3>
                <p className="text-sm text-gray-600">{zone.description}</p>
                <p className="text-xs text-gray-500">
                  {t(`zones.${zone.zone_type}`)} • {zone.radius_meters}m radius
                </p>
              </div>
            </Popup>
          </Circle>
        ))}

        {/* Render user markers */}
        {liveUsers.map((user) => (
          <UserMarker
            key={user.id}
            user={user}
            onClick={onUserClick}
          />
        ))}

        {/* Render movement trails */}
        {movementTrails.map((trail, index) => (
          <MovementTrail
            key={index}
            trail={trail.points}
            color={trail.color || '#3b82f6'}
          />
        ))}

        {/* Render heatmap layer - commented out due to missing dependency */}
        {/* {showHeatmap && <HeatmapLayer data={heatmapData} map={mapInstance} />} */}

        {/* Render dwell time overlays */}
        {showDwellTimes && <DwellTimeOverlay dwellTimes={dwellTimes} />}
      </MapContainer>

      {/* Map Controls */}
      <MapControls
        onDrawMode={() => {
          setIsDrawing(!isDrawing);
          setIsEditing(false);
          setSelectedZone(null);
        }}
        onEditMode={() => {
          setIsEditing(!isEditing);
          setIsDrawing(false);
          setSelectedZone(null);
        }}
        onDeleteMode={() => {
          setIsDeleting(!isDeleting);
          setIsDrawing(false);
          setIsEditing(false);
        }}
        isDrawing={isDrawing}
        isEditing={isEditing}
        showHeatmap={showHeatmap}
        onToggleHeatmap={() => setShowHeatmap(!showHeatmap)}
        showDwellTimes={showDwellTimes}
        onToggleDwellTimes={() => setShowDwellTimes(!showDwellTimes)}
      />

      {/* Zone Info Panel */}
      <ZoneInfoPanel
        zone={selectedZone}
        onClose={() => {
          setSelectedZone(null);
          setIsEditingZone(false);
        }}
        onEdit={handleZoneEdit}
        onDelete={handleZoneDelete}
        isEditing={isEditingZone}
        onSave={handleZoneEditSave}
        onCancel={handleZoneEditCancel}
      />

      {/* Loading overlay */}
      {loading && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-[2000]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-cyan"></div>
        </div>
      )}

      {/* Map Status */}
      <Glassmorphism className="absolute bottom-4 left-4 z-[1000] p-3">
        <div className="flex items-center space-x-4 text-sm text-gray-300">
          <div className="flex items-center space-x-1">
            <Target className="w-4 h-4" />
            <span>{liveZones.length} {t('nav.zones')}</span>
          </div>
          <div className="flex items-center space-x-1">
            <Users className="w-4 h-4" />
            <span>{liveUsers.length} {t('nav.users')}</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span>{isConnected ? t('map.live') : t('map.offline')}</span>
          </div>
          {isDrawing && (
            <div className="text-blue-400">
              {t('map.draw_zone_cancel')}
            </div>
          )}
        </div>
      </Glassmorphism>
    </div>
  );
};

export default MapView;