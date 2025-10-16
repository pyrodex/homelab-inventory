import { VALIDATION } from '../config/env';

/**
 * Sanitize string input to prevent XSS attacks
 * @param {string} input - User input string
 * @returns {string} Sanitized string
 */
export const sanitizeString = (input) => {
  if (typeof input !== 'string') return '';
  
  // Remove any HTML tags
  const withoutTags = input.replace(/<[^>]*>/g, '');
  
  // Escape special characters
  const div = document.createElement('div');
  div.textContent = withoutTags;
  return div.innerHTML;
};

/**
 * Validate and sanitize device name
 * @param {string} name - Device name
 * @returns {Object} Validation result
 */
export const validateDeviceName = (name) => {
  if (!name || typeof name !== 'string') {
    return { valid: false, error: 'Device name is required' };
  }
  
  const trimmed = name.trim();
  
  if (trimmed.length < VALIDATION.minNameLength) {
    return { 
      valid: false, 
      error: `Device name must be at least ${VALIDATION.minNameLength} characters` 
    };
  }
  
  if (trimmed.length > VALIDATION.maxNameLength) {
    return { 
      valid: false, 
      error: `Device name must not exceed ${VALIDATION.maxNameLength} characters` 
    };
  }
  
  // Check for malicious patterns
  const dangerousPatterns = /<script|javascript:|on\w+=/i;
  if (dangerousPatterns.test(trimmed)) {
    return { valid: false, error: 'Invalid characters detected' };
  }
  
  return { valid: true, value: sanitizeString(trimmed) };
};

/**
 * Validate IP address or hostname
 * @param {string} address - IP address or hostname
 * @returns {Object} Validation result
 */
export const validateAddress = (address) => {
  if (!address || typeof address !== 'string') {
    return { valid: false, error: 'Address is required' };
  }
  
  const trimmed = address.trim();
  
  // Check for port in address
  const [host, port] = trimmed.split(':');
  
  // Validate port if present
  if (port) {
    const portNum = parseInt(port, 10);
    if (isNaN(portNum) || portNum < VALIDATION.portMin || portNum > VALIDATION.portMax) {
      return { valid: false, error: 'Invalid port number' };
    }
  }
  
  // Validate IP address
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (ipPattern.test(host)) {
    const parts = host.split('.');
    const validIp = parts.every(part => {
      const num = parseInt(part, 10);
      return num >= 0 && num <= 255;
    });
    
    if (!validIp) {
      return { valid: false, error: 'Invalid IP address' };
    }
    
    return { valid: true, value: sanitizeString(trimmed) };
  }
  
  // Validate hostname
  const hostnamePattern = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
  if (hostnamePattern.test(host)) {
    return { valid: true, value: sanitizeString(trimmed) };
  }
  
  return { valid: false, error: 'Invalid IP address or hostname' };
};

/**
 * Validate port number
 * @param {number|string} port - Port number
 * @returns {Object} Validation result
 */
export const validatePort = (port) => {
  if (port === null || port === undefined || port === '') {
    return { valid: true, value: null }; // Port is optional
  }
  
  const portNum = parseInt(port, 10);
  
  if (isNaN(portNum)) {
    return { valid: false, error: 'Port must be a number' };
  }
  
  if (portNum < VALIDATION.portMin || portNum > VALIDATION.portMax) {
    return { 
      valid: false, 
      error: `Port must be between ${VALIDATION.portMin} and ${VALIDATION.portMax}` 
    };
  }
  
  return { valid: true, value: portNum };
};

/**
 * Validate serial number
 * @param {string} serialNumber - Serial number
 * @returns {Object} Validation result
 */
export const validateSerialNumber = (serialNumber) => {
  if (!serialNumber || typeof serialNumber !== 'string') {
    return { valid: false, error: 'Serial number is required' };
  }
  
  const trimmed = serialNumber.trim();
  
  if (trimmed.length > VALIDATION.maxSerialNumberLength) {
    return { 
      valid: false, 
      error: `Serial number must not exceed ${VALIDATION.maxSerialNumberLength} characters` 
    };
  }
  
  // Only allow alphanumeric, hyphens, and underscores
  const validPattern = /^[a-zA-Z0-9_-]+$/;
  if (!validPattern.test(trimmed)) {
    return { 
      valid: false, 
      error: 'Serial number can only contain letters, numbers, hyphens, and underscores' 
    };
  }
  
  return { valid: true, value: sanitizeString(trimmed) };
};

/**
 * Rate limiter class for API requests
 */
export class RateLimiter {
  constructor(maxRequests = 100, windowMs = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
    this.requests = [];
  }
  
  /**
   * Check if request is allowed
   * @returns {boolean} True if request is allowed
   */
  isAllowed() {
    const now = Date.now();
    
    // Remove old requests outside the time window
    this.requests = this.requests.filter(
      timestamp => now - timestamp < this.windowMs
    );
    
    // Check if we're under the limit
    if (this.requests.length < this.maxRequests) {
      this.requests.push(now);
      return true;
    }
    
    return false;
  }
  
  /**
   * Get remaining requests in current window
   * @returns {number} Remaining requests
   */
  getRemaining() {
    const now = Date.now();
    this.requests = this.requests.filter(
      timestamp => now - timestamp < this.windowMs
    );
    return Math.max(0, this.maxRequests - this.requests.length);
  }
}

/**
 * Escape HTML special characters
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
export const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;',
  };
  return String(text).replace(/[&<>"'/]/g, (char) => map[char]);
};

/**
 * Generate a secure random string
 * @param {number} length - Length of the string
 * @returns {string} Random string
 */
export const generateSecureId = (length = 16) => {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
};

/**
 * Check if string contains SQL injection patterns
 * @param {string} input - Input to check
 * @returns {boolean} True if potentially malicious
 */
export const containsSqlInjection = (input) => {
  if (typeof input !== 'string') return false;
  
  const sqlPatterns = [
    /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)/i,
    /(--|;|\/\*|\*\/)/,
    /(\bOR\b.*=.*)/i,
    /(\bUNION\b.*\bSELECT\b)/i,
  ];
  
  return sqlPatterns.some(pattern => pattern.test(input));
};

/**
 * Validate and sanitize form data
 * @param {Object} formData - Form data to validate
 * @returns {Object} Validation results
 */
export const validateFormData = (formData) => {
  const errors = {};
  
  // Validate name
  const nameValidation = validateDeviceName(formData.name);
  if (!nameValidation.valid) {
    errors.name = nameValidation.error;
  }
  
  // Validate address
  const addressValidation = validateAddress(formData.ip_address);
  if (!addressValidation.valid) {
    errors.ip_address = addressValidation.error;
  }
  
  // Validate serial number
  const serialValidation = validateSerialNumber(formData.serial_number);
  if (!serialValidation.valid) {
    errors.serial_number = serialValidation.error;
  }
  
  // Check for SQL injection attempts
  Object.entries(formData).forEach(([key, value]) => {
    if (typeof value === 'string' && containsSqlInjection(value)) {
      errors[key] = 'Invalid input detected';
    }
  });
  
  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
};

export default {
  sanitizeString,
  validateDeviceName,
  validateAddress,
  validatePort,
  validateSerialNumber,
  validateFormData,
  RateLimiter,
  escapeHtml,
  generateSecureId,
  containsSqlInjection,
};
