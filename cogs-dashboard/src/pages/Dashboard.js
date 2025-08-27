import React, { useState, useEffect } from 'react';
import { useClient } from '../contexts/ClientContext';

const Dashboard = () => {
  const { client, logout } = useClient();
  const [currentView, setCurrentView] = useState('dashboard');
  const [recentFiles, setRecentFiles] = useState([]);

  useEffect(() => {
    // Load recent files for this client
    loadRecentFiles();
  }, [client]);

  const loadRecentFiles = () => {
    // In production this would be an API call
    const files = JSON.parse(localStorage.getItem(`files_${client.client_id}`) || '[]');
    setRecentFiles(files);
  };

  const loadRecentRuns = () => {
    // Load FIFO calculation results instead of just files
    const results = JSON.parse(localStorage.getItem(`results_${client.client_id}`) || '[]');
    return results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  };

  const formatRunPeriod = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long'
    });
  };

  const navigateTo = (view) => {
    setCurrentView(view);
  };

  if (currentView === 'upload') {
    return <UploadPage onBack={() => setCurrentView('dashboard')} />;
  }

  if (currentView === 'download') {
    return <DownloadPage onBack={() => setCurrentView('dashboard')} />;
  }

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6' }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'white',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '1rem 2rem'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              backgroundColor: '#10b981',
              color: 'white',
              padding: '0.5rem',
              borderRadius: '4px',
              fontWeight: 'bold',
              fontSize: '0.875rem'
            }}>
              [FL]
            </div>
            <h1 style={{ color: '#0f172a', margin: 0 }}>FirstLot</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: '#6b7280' }}>
              {client.company_name}
            </span>
            <button
              onClick={logout}
              style={{
                backgroundColor: '#ef4444',
                color: 'white',
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ padding: '2rem' }}>
        {/* Quick Actions */}
        <div style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          marginBottom: '2rem'
        }}>
          <h2 style={{ color: '#1f2937', marginBottom: '1.5rem' }}>Quick Actions</h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem'
          }}>
            <ActionCard
              title="Start FIFO Run"
              description="Upload purchase lots & sales data"
              buttonText="Upload & Process"
              onClick={() => window.location.href = '/upload'}
              color="#10b981"
            />
            <ActionCard
              title="Lot History"
              description="View inventory lots and consumption"
              buttonText="View Lots"
              onClick={() => window.location.href = '/lot-history'}
              color="#3b82f6"
            />
            <ActionCard
              title="Monthly COGS"
              description="Track cost trends over time"
              buttonText="View COGS"
              onClick={() => window.location.href = '/monthly-cogs'}
              color="#8b5cf6"
            />
            <ActionCard
              title="Download Reports"
              description="Get your COGS calculations"
              buttonText={loadRecentRuns().length > 0 ? "View Reports" : "No Reports Yet"}
              onClick={() => window.location.href = '/download'}
              color={loadRecentRuns().length > 0 ? "#10b981" : "#9ca3af"}
              disabled={loadRecentRuns().length === 0}
            />
          </div>
        </div>

        {/* Recent FIFO Runs */}
        <div style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <h2 style={{ color: '#1f2937', marginBottom: '1.5rem' }}>Recent FIFO Runs</h2>
          {loadRecentRuns().length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Period</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>SKUs</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Total COGS</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {loadRecentRuns().slice(0, 5).map((run, index) => (
                    <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '0.75rem', color: '#1f2937' }}>
                        {formatRunPeriod(run.timestamp)}
                      </td>
                      <td style={{ padding: '0.75rem', color: '#6b7280' }}>{run.processed_skus}</td>
                      <td style={{ padding: '0.75rem', color: '#6b7280' }}>
                        ${run.total_cogs?.toFixed(2) || '0.00'}
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <StatusBadge status="completed" />
                      </td>
                      <td style={{ padding: '0.75rem' }}>
                        <button
                          onClick={() => navigateTo('download')}
                          style={{
                            backgroundColor: '#10b981',
                            color: 'white',
                            padding: '0.25rem 0.75rem',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.875rem'
                          }}
                        >
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '3rem',
              color: '#6b7280'
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📊</div>
              <h3 style={{ color: '#1f2937', marginBottom: '0.5rem' }}>No FIFO Runs Yet</h3>
              <p style={{ marginBottom: '2rem' }}>
                Upload your purchase lots and sales data to get started with FIFO costing.
              </p>
              <button
                onClick={() => navigateTo('upload')}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.75rem 2rem',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  fontWeight: '600'
                }}
              >
                🚀 Start Your First FIFO Run
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

const ActionCard = ({ title, description, buttonText, onClick, color, disabled = false }) => (
  <div style={{
    padding: '1.5rem',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    textAlign: 'center'
  }}>
    <h3 style={{ color: '#1f2937', marginBottom: '0.5rem' }}>{title}</h3>
    <p style={{ color: '#6b7280', marginBottom: '1rem', fontSize: '0.875rem' }}>
      {description}
    </p>
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      style={{
        backgroundColor: color,
        color: 'white',
        padding: '0.75rem 1.5rem',
        border: 'none',
        borderRadius: '4px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        width: '100%',
        opacity: disabled ? 0.6 : 1
      }}
    >
      {buttonText}
    </button>
  </div>
);

const StatusBadge = ({ status }) => {
  const colors = {
    uploaded: { bg: '#dbeafe', text: '#1e40af' },
    processing: { bg: '#fef3c7', text: '#d97706' },
    completed: { bg: '#d1fae5', text: '#059669' },
    error: { bg: '#fee2e2', text: '#dc2626' }
  };

  const style = colors[status] || colors.uploaded;

  return (
    <span style={{
      backgroundColor: style.bg,
      color: style.text,
      padding: '0.25rem 0.75rem',
      borderRadius: '9999px',
      fontSize: '0.75rem',
      fontWeight: '500'
    }}>
      {status}
    </span>
  );
};

// Import components that will be created
const UploadPage = ({ onBack }) => (
  <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6', padding: '2rem' }}>
    <button onClick={onBack} style={{ marginBottom: '1rem' }}>← Back to Dashboard</button>
    <div style={{
      backgroundColor: 'white',
      padding: '2rem',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
    }}>
      <h1>Upload Files</h1>
      <p>Upload functionality will be implemented next...</p>
    </div>
  </div>
);

const DownloadPage = ({ onBack }) => (
  <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6', padding: '2rem' }}>
    <button onClick={onBack} style={{ marginBottom: '1rem' }}>← Back to Dashboard</button>
    <div style={{
      backgroundColor: 'white',
      padding: '2rem',
      borderRadius: '8px',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
    }}>
      <h1>Download Results</h1>
      <p>Download functionality will be implemented next...</p>
    </div>
  </div>
);

export default Dashboard;