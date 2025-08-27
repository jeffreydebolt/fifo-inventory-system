import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ClientProvider, useClient } from './contexts/ClientContext';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import DownloadPage from './pages/DownloadPage';
import LotHistoryPage from './pages/LotHistoryPage';
import MonthlyCogsPage from './pages/MonthlyCogsPage';

function AppContent() {
  const { isAuthenticated, loading } = useClient();

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f3f4f6'
      }}>
        <div>Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/download" element={<DownloadPage />} />
        <Route path="/lot-history" element={<LotHistoryPage />} />
        <Route path="/monthly-cogs" element={<MonthlyCogsPage />} />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <ClientProvider>
      <AppContent />
    </ClientProvider>
  );
}

export default App;