import React from 'react';
import { AlertCircle, X } from 'lucide-react';

function ErrorAlert({ message, onClose }) {
  if (!message) return null;
  
  return (
    <div className="fixed top-4 left-4 right-4 md:right-4 md:left-auto z-50 max-w-md md:max-w-md mx-auto md:mx-0">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-red-800 mb-1">Error</h3>
            <p className="text-sm text-red-700 whitespace-pre-line break-words">{message}</p>
          </div>
          <button 
            onClick={onClose} 
            className="text-red-400 active:text-red-600 transition-colors touch-manipulation min-w-[44px] min-h-[44px] flex items-center justify-center flex-shrink-0"
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
