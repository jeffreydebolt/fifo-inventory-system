import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Kill any service worker to prevent stale bundle caching
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);