import React from 'react';
import { AlertCircle, X } from 'lucide-react';

function ErrorAlert({ message, onClose }) {
  if (!message) return null;
  
  return (
    <div className="fixed top-4 right-4 z-50 max-w-md">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-800 mb-1">Error</h3>
            <p className="text-sm text-red-700 whitespace-pre-line">{message}</p>
          </div>
          <button 
            onClick={onClose} 
            className="text-red-400 hover:text-red-600 transition-colors"
            aria-label="Close error message"
          >
            <X size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ErrorAlert;
