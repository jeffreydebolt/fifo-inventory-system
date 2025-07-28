import React from 'react';
import ReactDOM from 'react-dom/client';
import * as Sentry from '@sentry/react';
import './index.css';
import App from './App';

// Initialize Sentry
if (process.env.REACT_APP_SENTRY_DSN) {
  Sentry.init({
    dsn: process.env.REACT_APP_SENTRY_DSN,
    integrations: [
      new Sentry.BrowserTracing(),
    ],
    tracesSampleRate: 0.1,
    environment: process.env.NODE_ENV,
    release: process.env.REACT_APP_VERSION || '1.0.0',
  });
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
