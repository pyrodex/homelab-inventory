import React, { useState, useEffect } from 'react';
import { X, Edit2, Trash2 } from 'lucide-react';
import { vendorApi, modelApi, locationApi } from '../../../services/api';

function AdminModal({ onClose, onError }) {
  const [activeTab, setActiveTab] = useState('vendors');
  const [vendors, setVendors] = useState([]);
  const [models, setModels] = useState([]);
  const [locations, setLocations] = useState([]);
  const [newVendorName, setNewVendorName] = useState('');
  const [newModelName, setNewModelName] = useState('');
  const [newLocationName, setNewLocationName] = useState('');
  const [selectedVendorForModel, setSelectedVendorForModel] = useState('');
  const [editingVendor, setEditingVendor] = useState(null);
  const [editingModel, setEditingModel] = useState(null);
  const [editingLocation, setEditingLocation] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { 
    loadData(); 
  }, []);

  const loadData = async () => { 
    setLoading(true); 
    await Promise.all([
      loadVendors(), 
      loadModels(), 
      loadLocations()
    ]); 
    setLoading(false); 
  };

  const loadVendors = async () => {
    try {
      const data = await vendorApi.getAll();
      setVendors(data);
    } catch (err) {
      console.error('Failed to load vendors:', err);
    }
  };

  const loadModels = async () => {
    try {
      const data = await modelApi.getAll();
      const sortedData = data.sort((a, b) => {
        const vendorCompare = (a.vendor_name || '').localeCompare(b.vendor_name || '');
        if (vendorCompare !== 0) return vendorCompare;
        return (a.name || '').localeCompare(b.name || '');
      });
      setModels(sortedData);
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadLocations = async () => {
    try {
      const data = await locationApi.getAll();
      setLocations(data);
    } catch (err) {
      console.error('Failed to load locations:', err);
    }
  };

  const addVendor = async () => {
    if (!newVendorName.trim()) return;
    
    try {
      await vendorApi.create(newVendorName.trim());
      setNewVendorName('');
      loadVendors();
    } catch (err) {
      onError(err.message || 'Failed to add vendor');
    }
  };

  const updateVendor = async (id, name) => {
    try {
      await vendorApi.update(id, name);
      setEditingVendor(null);
      loadVendors();
    } catch (err) {
      onError(err.message || 'Failed to update vendor');
    }
  };

  const deleteVendor = async (id) => {
    if (!window.confirm('Are you sure you want to delete this vendor? This will also delete all associated models.')) {
      return;
    }
    
    try {
      await vendorApi.delete(id);
      loadVendors();
      loadModels();
    } catch (err) {
      onError(err.message || 'Failed to delete vendor');
    }
  };

  const addModel = async () => {
    if (!newModelName.trim() || !selectedVendorForModel) return;
    
    try {
      await modelApi.create(newModelName.trim(), parseInt(selectedVendorForModel));
      setNewModelName('');
      setSelectedVendorForModel('');
      loadModels();
    } catch (err) {
      onError(err.message || 'Failed to add model');
    }
  };

  const updateModel = async (id, name, vendorId) => {
    try {
      await modelApi.update(id, name, vendorId);
      setEditingModel(null);
      loadModels();
    } catch (err) {
      onError(err.message || 'Failed to update model');
    }
  };

  const deleteModel = async (id) => {
    if (!window.confirm('Are you sure you want to delete this model?')) {
      return;
    }
    
    try {
      await modelApi.delete(id);
      loadModels();
    } catch (err) {
      onError(err.message || 'Failed to delete model');
    }
  };

  const addLocation = async () => {
    if (!newLocationName.trim()) return;
    
    try {
      await locationApi.create(newLocationName.trim());
      setNewLocationName('');
      loadLocations();
    } catch (err) {
      onError(err.message || 'Failed to add location');
    }
  };

  const updateLocation = async (id, name) => {
    try {
      await locationApi.update(id, name);
      setEditingLocation(null);
      loadLocations();
    } catch (err) {
      onError(err.message || 'Failed to update location');
    }
  };

  const deleteLocation = async (id) => {
    if (!window.confirm('Are you sure you want to delete this location?')) {
      return;
    }
    
    try {
      await locationApi.delete(id);
      loadLocations();
    } catch (err) {
      onError(err.message || 'Failed to delete location');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">Administration</h2>
            <button 
              onClick={onClose} 
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close admin panel"
            >
              <X size={24} />
            </button>
          </div>
          <div className="flex gap-2 mt-4">
            <button 
              onClick={() => setActiveTab('vendors')} 
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'vendors' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Vendors
            </button>
            <button 
              onClick={() => setActiveTab('models')} 
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'models' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Models
            </button>
            <button 
              onClick={() => setActiveTab('locations')} 
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === 'locations' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              Locations
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-12">
              <p className="text-gray-600">Loading...</p>
            </div>
          ) : activeTab === 'vendors' ? (
            <VendorsTab
              vendors={vendors}
              newVendorName={newVendorName}
              setNewVendorName={setNewVendorName}
              editingVendor={editingVendor}
              setEditingVendor={setEditingVendor}
              addVendor={addVendor}
              updateVendor={updateVendor}
              deleteVendor={deleteVendor}
            />
          ) : activeTab === 'models' ? (
            <ModelsTab
              models={models}
              vendors={vendors}
              newModelName={newModelName}
              setNewModelName={setNewModelName}
              selectedVendorForModel={selectedVendorForModel}
              setSelectedVendorForModel={setSelectedVendorForModel}
              editingModel={editingModel}
              setEditingModel={setEditingModel}
              addModel={addModel}
              updateModel={updateModel}
              deleteModel={deleteModel}
            />
          ) : (
            <LocationsTab
              locations={locations}
              newLocationName={newLocationName}
              setNewLocationName={setNewLocationName}
              editingLocation={editingLocation}
              setEditingLocation={setEditingLocation}
              addLocation={addLocation}
              updateLocation={updateLocation}
              deleteLocation={deleteLocation}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function VendorsTab({ 
  vendors, 
  newVendorName, 
  setNewVendorName, 
  editingVendor, 
  setEditingVendor, 
  addVendor, 
  updateVendor, 
  deleteVendor 
}) {
  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Add New Vendor</h3>
        <div className="flex gap-2">
          <input 
            type="text" 
            value={newVendorName} 
            onChange={(e) => setNewVendorName(e.target.value)} 
            placeholder="Vendor name" 
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
            onKeyPress={(e) => e.key === 'Enter' && addVendor()} 
          />
          <button 
            onClick={addVendor} 
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Add
          </button>
        </div>
      </div>
      
      <div>
        <h3 className="text-lg font-semibold mb-3">Existing Vendors ({vendors.length})</h3>
        <div className="space-y-2">
          {vendors.map(vendor => (
            <div key={vendor.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              {editingVendor === vendor.id ? (
                <input 
                  type="text" 
                  defaultValue={vendor.name} 
                  onBlur={(e) => updateVendor(vendor.id, e.target.value)} 
                  onKeyPress={(e) => { 
                    if (e.key === 'Enter') { 
                      updateVendor(vendor.id, e.target.value); 
                    } 
                  }} 
                  className="flex-1 px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  autoFocus 
                />
              ) : (
                <div className="flex-1">
                  <span className="font-medium">{vendor.name}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    ({vendor.model_count} models, {vendor.device_count} devices)
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <button 
                  onClick={() => setEditingVendor(vendor.id)} 
                  className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                  aria-label="Edit vendor"
                >
                  <Edit2 size={16} />
                </button>
                <button 
                  onClick={() => deleteVendor(vendor.id)} 
                  className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                  aria-label="Delete vendor"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {vendors.length === 0 && (
            <p className="text-gray-500 text-center py-4">
              No vendors yet. Add your first vendor above.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function ModelsTab({ 
  models, 
  vendors, 
  newModelName, 
  setNewModelName, 
  selectedVendorForModel, 
  setSelectedVendorForModel, 
  editingModel, 
  setEditingModel, 
  addModel, 
  updateModel, 
  deleteModel 
}) {
  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Add New Model</h3>
        {vendors.length === 0 ? (
          <p className="text-amber-600 bg-amber-50 p-3 rounded-lg">
            Please add at least one vendor first before adding models.
          </p>
        ) : (
          <div className="flex gap-2">
            <select 
              value={selectedVendorForModel} 
              onChange={(e) => setSelectedVendorForModel(e.target.value)} 
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select Vendor...</option>
              {vendors.map(vendor => (
                <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
              ))}
            </select>
            <input 
              type="text" 
              value={newModelName} 
              onChange={(e) => setNewModelName(e.target.value)} 
              placeholder="Model name" 
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
              onKeyPress={(e) => e.key === 'Enter' && addModel()} 
            />
            <button 
              onClick={addModel} 
              disabled={!selectedVendorForModel} 
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              Add
            </button>
          </div>
        )}
      </div>
      
      <div>
        <h3 className="text-lg font-semibold mb-3">Existing Models ({models.length})</h3>
        <div className="space-y-2">
          {models.map(model => (
            <div key={model.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              {editingModel === model.id ? (
                <div className="flex-1 flex gap-2">
                  <select 
                    defaultValue={model.vendor_id} 
                    onBlur={(e) => updateModel(model.id, model.name, e.target.value)} 
                    className="px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {vendors.map(vendor => (
                      <option key={vendor.id} value={vendor.id}>{vendor.name}</option>
                    ))}
                  </select>
                  <input 
                    type="text" 
                    defaultValue={model.name} 
                    onBlur={(e) => updateModel(model.id, e.target.value, model.vendor_id)} 
                    onKeyPress={(e) => { 
                      if (e.key === 'Enter') { 
                        updateModel(model.id, e.target.value, model.vendor_id); 
                      } 
                    }} 
                    className="flex-1 px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                    autoFocus 
                  />
                </div>
              ) : (
                <div className="flex-1">
                  <span className="font-medium">{model.vendor_name}</span>
                  <span className="text-gray-400 mx-2">→</span>
                  <span className="font-medium">{model.name}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    ({model.device_count} devices)
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <button 
                  onClick={() => setEditingModel(model.id)} 
                  className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                  aria-label="Edit model"
                >
                  <Edit2 size={16} />
                </button>
                <button 
                  onClick={() => deleteModel(model.id)} 
                  className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                  aria-label="Delete model"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {models.length === 0 && (
            <p className="text-gray-500 text-center py-4">
              No models yet. Add your first model above.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function LocationsTab({ 
  locations, 
  newLocationName, 
  setNewLocationName, 
  editingLocation, 
  setEditingLocation, 
  addLocation, 
  updateLocation, 
  deleteLocation 
}) {
  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">Add New Location</h3>
        <div className="flex gap-2">
          <input 
            type="text" 
            value={newLocationName} 
            onChange={(e) => setNewLocationName(e.target.value)} 
            placeholder="Location name (e.g., Data Center, Office, Rack 1)" 
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
            onKeyPress={(e) => e.key === 'Enter' && addLocation()} 
          />
          <button 
            onClick={addLocation} 
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            Add
          </button>
        </div>
      </div>
      
      <div>
        <h3 className="text-lg font-semibold mb-3">Existing Locations ({locations.length})</h3>
        <div className="space-y-2">
          {locations.map(location => (
            <div key={location.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              {editingLocation === location.id ? (
                <input 
                  type="text" 
                  defaultValue={location.name} 
                  onBlur={(e) => updateLocation(location.id, e.target.value)} 
                  onKeyPress={(e) => { 
                    if (e.key === 'Enter') { 
                      updateLocation(location.id, e.target.value); 
                    } 
                  }} 
                  className="flex-1 px-3 py-1 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent" 
                  autoFocus 
                />
              ) : (
                <div className="flex-1">
                  <span className="font-medium">{location.name}</span>
                  <span className="text-sm text-gray-500 ml-2">
                    ({location.device_count} devices)
                  </span>
                </div>
              )}
              <div className="flex gap-2">
                <button 
                  onClick={() => setEditingLocation(location.id)} 
                  className="p-1 text-blue-600 hover:bg-blue-100 rounded transition-colors"
                  aria-label="Edit location"
                >
                  <Edit2 size={16} />
                </button>
                <button 
                  onClick={() => deleteLocation(location.id)} 
                  className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                  aria-label="Delete location"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
          {locations.length === 0 && (
            <p className="text-gray-500 text-center py-4">
              No locations yet. Add your first location above.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminModal;
