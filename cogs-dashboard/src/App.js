import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import AuthGuard from './components/AuthGuard';
import Layout from './components/Layout';
import Home from './pages/Home';
import Login from './pages/Login';
import Upload from './pages/Upload';
import './App.css';


// Placeholder components for routes not yet implemented
const RunsList = () => (
  <div className="text-center py-12">
    <h2 className="text-xl font-semibold text-gray-900">Runs List</h2>
    <p className="text-gray-600 mt-2">Coming soon...</p>
  </div>
);

const RunDetail = () => (
  <div className="text-center py-12">
    <h2 className="text-xl font-semibold text-gray-900">Run Detail</h2>
    <p className="text-gray-600 mt-2">Coming soon...</p>
  </div>
);

const Settings = () => (
  <div className="text-center py-12">
    <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
    <p className="text-gray-600 mt-2">Coming soon...</p>
  </div>
);

const Signup = () => (
  <div className="text-center py-12">
    <h2 className="text-xl font-semibold text-gray-900">Sign Up</h2>
    <p className="text-gray-600 mt-2">Coming soon...</p>
  </div>
);

function App() {
  return (
    <AuthGuard>
      <Router>
        <div className="App">
          <Layout>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              {/* Protected routes */}
              <Route path="/" element={<Home />} />
              <Route path="/runs" element={<RunsList />} />
              <Route path="/runs/:runId" element={<RunDetail />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/settings" element={<Settings />} />

              {/* Catch all route */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>

          {/* Global toast notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                theme: {
                  primary: 'green',
                  secondary: 'black',
                },
              },
            }}
          />
        </div>
      </Router>
    </AuthGuard>
  );
}

export default App;