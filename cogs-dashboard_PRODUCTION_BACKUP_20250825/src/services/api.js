import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor to add auth headers if needed
api.interceptors.request.use(
  (config) => {
    // Could add auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 409:
          throw new Error(data.detail || 'A run is already in progress for this tenant');
        case 404:
          throw new Error(data.detail || 'Resource not found');
        case 400:
          throw new Error(data.detail || 'Invalid request');
        case 500:
          throw new Error('Server error. Please try again later.');
        default:
          throw new Error(data.detail || `Request failed with status ${status}`);
      }
    } else if (error.request) {
      throw new Error('Network error. Please check your connection.');
    } else {
      throw new Error('Request failed. Please try again.');
    }
  }
);

export default api;