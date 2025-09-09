import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ClientProvider } from './contexts/ClientContext';
import LoginPage from './pages/LoginPage';
import UploadPage from './pages/UploadPage';

function App() {
  return (
    <ClientProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route path="/upload" element={<UploadPage />} />
        </Routes>
      </Router>
    </ClientProvider>
  );
}

export default App;