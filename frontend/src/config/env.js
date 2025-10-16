/**
 * Environment configuration
 * Centralizes all environment-specific settings
 */

// API Configuration
export const API_CONFIG = {
  baseUrl: process.env.REACT_APP_API_URL || '/api',
  timeout: process.env.REACT_APP_API_TIMEOUT || 30000,
  retryAttempts: process.env.REACT_APP_API_RETRY_ATTEMPTS || 3,
};

// Feature Flags
export const FEATURES = {
  enableDebugMode: process.env.REACT_APP_DEBUG === 'true',
  enableAnalytics: process.env.REACT_APP_ANALYTICS === 'true',
  maxDevicesPerPage: parseInt(process.env.REACT_APP_MAX_DEVICES_PER_PAGE || '100', 10),
};

// Security Configuration
export const SECURITY = {
  // Content Security Policy
  csp: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'unsafe-inline'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", 'data:', 'https:'],
    connectSrc: ["'self'"],
  },
  
  // Rate limiting (client-side)
  rateLimit: {
    maxRequests: 100,
    windowMs: 60000, // 1 minute
  },
  
  // Session timeout (in milliseconds)
  sessionTimeout: parseInt(process.env.REACT_APP_SESSION_TIMEOUT || '3600000', 10), // 1 hour default
};

// App Configuration
export const APP_CONFIG = {
  appName: 'Homelab Inventory',
  version: process.env.REACT_APP_VERSION || '1.0.0',
  environment: process.env.NODE_ENV || 'development',
};

// Validation
export const VALIDATION = {
  maxNameLength: 100,
  maxSerialNumberLength: 100,
  maxFunctionLength: 200,
  minNameLength: 2,
  portMin: 1,
  portMax: 65535,
};

// Export all configs
export default {
  API_CONFIG,
  FEATURES,
  SECURITY,
  APP_CONFIG,
  VALIDATION,
};
