import React, { useState } from 'react';
import { X, Upload, Download, Trash2, FileText, FileJson } from 'lucide-react';
import { bulkApi } from '../../../services/api';
import { downloadBlob } from '../../../utils/helpers';
import { DEVICE_TYPES } from '../../../constants/deviceTypes';

function BulkOperationsModal({ onClose, onSuccess, onError }) {
  const [activeTab, setActiveTab] = useState('import');
  const [importFile, setImportFile] = useState(null);
  const [importJson, setImportJson] = useState('');
  const [importFormat, setImportFormat] = useState('json');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [exportFormat, setExportFormat] = useState('json');
  const [exportType, setExportType] = useState('all');
  const [exporting, setExporting] = useState(false);
  const [deleteIds, setDeleteIds] = useState('');
  const [deleting, setDeleting] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImportFile(file);
    }
  };

  const handleImport = async () => {
    setImporting(true);
    setImportResult(null);
    
    try {
      let result;
      if (importFormat === 'json') {
        const devices = JSON.parse(importJson);
        result = await bulkApi.importDevices(devices);
      } else {
        result = await bulkApi.importDevicesCSV(importFile);
      }
      
      setImportResult(result);
      if (result.created > 0) {
        onSuccess(`Successfully imported ${result.created} device(s)`);
        setTimeout(() => {
          onClose();
        }, 2000);
      }
    } catch (err) {
      onError(err.message || 'Failed to import devices');
    } finally {
      setImporting(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    
    try {
      if (exportFormat === 'csv') {
        const blob = await bulkApi.exportDevices(exportFormat, exportType === 'all' ? null : exportType);
        downloadBlob(blob, `devices_export_${exportType}.csv`);
      } else {
        const data = await bulkApi.exportDevices(exportFormat, exportType === 'all' ? null : exportType);
        const jsonStr = JSON.stringify(data, null, 2);
        downloadBlob(new Blob([jsonStr], { type: 'application/json' }), `devices_export_${exportType}.json`);
      }
      
      onSuccess(`Devices exported successfully as ${exportFormat.toUpperCase()}`);
    } catch (err) {
      onError(err.message || 'Failed to export devices');
    } finally {
      setExporting(false);
    }
  };

  const handleBulkDelete = async () => {
    const ids = deleteIds.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));
    
    if (ids.length === 0) {
      onError('Please enter at least one valid device ID');
      return;
    }
    
    if (!window.confirm(`Are you sure you want to delete ${ids.length} device(s)? This action cannot be undone.`)) {
      return;
    }
    
    setDeleting(true);
    
    try {
      const result = await bulkApi.deleteDevices(ids);
      onSuccess(`Successfully deleted ${result.deleted} device(s)`);
      setDeleteIds('');
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      onError(err.message || 'Failed to delete devices');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-0 md:p-4 z-50">
      <div className="bg-white rounded-none md:rounded-lg max-w-4xl w-full h-full md:h-auto max-h-[100vh] md:max-h-[90vh] overflow-y-auto modal-content">
        <div className="sticky top-0 bg-white z-10 p-4 md:p-6 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl md:text-2xl font-bold text-gray-900">Bulk Operations</h2>
          <button
            onClick={onClose}
            className="p-2 -mr-2 text-gray-400 hover:text-gray-600 active:text-gray-800 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Close modal"
          >
            <X size={24} />
          </button>
        </div>
        
        <div className="p-4 md:p-6">
          {/* Tabs */}
          <div className="flex flex-col md:flex-row gap-2 mb-6 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('import')}
              className={`px-4 py-2.5 rounded-t-lg font-medium transition-colors touch-manipulation min-h-[44px] ${
                activeTab === 'import'
                  ? 'bg-blue-600 text-white active:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 active:bg-gray-300'
              }`}
            >
              <Upload size={18} className="inline mr-2" />
              Import
            </button>
            <button
              onClick={() => setActiveTab('export')}
              className={`px-4 py-2.5 rounded-t-lg font-medium transition-colors touch-manipulation min-h-[44px] ${
                activeTab === 'export'
                  ? 'bg-blue-600 text-white active:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 active:bg-gray-300'
              }`}
            >
              <Download size={18} className="inline mr-2" />
              Export
            </button>
            <button
              onClick={() => setActiveTab('delete')}
              className={`px-4 py-2.5 rounded-t-lg font-medium transition-colors touch-manipulation min-h-[44px] ${
                activeTab === 'delete'
                  ? 'bg-blue-600 text-white active:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 active:bg-gray-300'
              }`}
            >
              <Trash2 size={18} className="inline mr-2" />
              Bulk Delete
            </button>
          </div>

          {/* Import Tab */}
          {activeTab === 'import' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Import Format
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer touch-manipulation min-h-[44px]">
                    <input
                      type="radio"
                      value="json"
                      checked={importFormat === 'json'}
                      onChange={(e) => setImportFormat(e.target.value)}
                      className="w-5 h-5"
                    />
                    <FileJson size={20} />
                    <span>JSON</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer touch-manipulation min-h-[44px]">
                    <input
                      type="radio"
                      value="csv"
                      checked={importFormat === 'csv'}
                      onChange={(e) => setImportFormat(e.target.value)}
                      className="w-5 h-5"
                    />
                    <FileText size={20} />
                    <span>CSV</span>
                  </label>
                </div>
              </div>

              {importFormat === 'json' ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    JSON Data (array of devices)
                  </label>
                  <textarea
                    value={importJson}
                    onChange={(e) => setImportJson(e.target.value)}
                    placeholder='[{"name": "Device 1", "device_type": "linux_server_physical", ...}, ...]'
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base font-mono text-sm min-h-[200px]"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Paste JSON array of device objects. Required fields: name, device_type, ip_address, function, vendor_id, model_id, location_id, serial_number
                  </p>
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    CSV File
                  </label>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleFileChange}
                    className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    CSV file with columns: name, device_type, ip_address, function, vendor, model, location, serial_number, networks, interface_type, poe_powered, poe_standards, monitoring_enabled
                  </p>
                </div>
              )}

              {importResult && (
                <div className={`p-4 rounded-lg ${
                  importResult.created > 0 ? 'bg-green-50 border border-green-200' : 'bg-yellow-50 border border-yellow-200'
                }`}>
                  <p className="font-medium mb-2">
                    Import Results: {importResult.created} created, {importResult.failed} failed
                  </p>
                  {importResult.failed_devices && importResult.failed_devices.length > 0 && (
                    <div className="text-sm mt-2">
                      <p className="font-medium">Failed:</p>
                      <ul className="list-disc list-inside mt-1">
                        {importResult.failed_devices.slice(0, 5).map((item, idx) => (
                          <li key={idx}>{item.name || item.index}: {JSON.stringify(item.error)}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={handleImport}
                disabled={importing || (importFormat === 'json' && !importJson.trim()) || (importFormat === 'csv' && !importFile)}
                className="w-full md:w-auto px-4 py-2.5 bg-blue-600 text-white rounded-lg active:bg-blue-700 transition-colors touch-manipulation min-h-[44px] disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {importing ? 'Importing...' : 'Import Devices'}
              </button>
            </div>
          )}

          {/* Export Tab */}
          {activeTab === 'export' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Export Format
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer touch-manipulation min-h-[44px]">
                    <input
                      type="radio"
                      value="json"
                      checked={exportFormat === 'json'}
                      onChange={(e) => setExportFormat(e.target.value)}
                      className="w-5 h-5"
                    />
                    <FileJson size={20} />
                    <span>JSON</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer touch-manipulation min-h-[44px]">
                    <input
                      type="radio"
                      value="csv"
                      checked={exportFormat === 'csv'}
                      onChange={(e) => setExportFormat(e.target.value)}
                      className="w-5 h-5"
                    />
                    <FileText size={20} />
                    <span>CSV</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter by Device Type (optional)
                </label>
                <select
                  value={exportType}
                  onChange={(e) => setExportType(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base touch-manipulation"
                >
                  <option value="all">All Devices</option>
                  {DEVICE_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              <button
                onClick={handleExport}
                disabled={exporting}
                className="w-full md:w-auto px-4 py-2.5 bg-green-600 text-white rounded-lg active:bg-green-700 transition-colors touch-manipulation min-h-[44px] disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {exporting ? 'Exporting...' : 'Export Devices'}
              </button>
            </div>
          )}

          {/* Delete Tab */}
          {activeTab === 'delete' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device IDs to Delete (comma-separated)
                </label>
                <input
                  type="text"
                  value={deleteIds}
                  onChange={(e) => setDeleteIds(e.target.value)}
                  placeholder="1, 2, 3, 4, 5"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Enter device IDs separated by commas. Maximum 100 devices at once.
                </p>
              </div>

              <button
                onClick={handleBulkDelete}
                disabled={deleting || !deleteIds.trim()}
                className="w-full md:w-auto px-4 py-2.5 bg-red-600 text-white rounded-lg active:bg-red-700 transition-colors touch-manipulation min-h-[44px] disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {deleting ? 'Deleting...' : 'Delete Devices'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default BulkOperationsModal;

