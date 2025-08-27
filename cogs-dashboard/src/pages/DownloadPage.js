import React, { useState, useEffect } from 'react';
import { useClient } from '../contexts/ClientContext';

const DownloadPage = () => {
  const { client } = useClient();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedResult, setSelectedResult] = useState(null);

  useEffect(() => {
    loadClientResults();
  }, [client]);

  const loadClientResults = () => {
    // Load results for this specific client
    const key = `results_${client.client_id}`;
    const clientResults = JSON.parse(localStorage.getItem(key) || '[]');
    
    // Sort by timestamp, newest first
    const sortedResults = clientResults.sort((a, b) => 
      new Date(b.timestamp) - new Date(a.timestamp)
    );
    
    setResults(sortedResults);
    setLoading(false);
  };

  const downloadCSV = (result) => {
    // Generate CSV content from FIFO result
    const csvContent = generateCSVFromResult(result);
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `COGS_Report_${client.client_id}_${formatTimestamp(result.timestamp)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAllResults = () => {
    if (results.length === 0) return;
    
    // Create a combined CSV with all results
    const combinedCSV = generateCombinedCSV(results);
    
    const blob = new Blob([combinedCSV], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `All_COGS_Reports_${client.client_id}_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const viewResult = (result) => {
    setSelectedResult(result);
  };

  const closeModal = () => {
    setSelectedResult(null);
  };

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6', padding: '2rem' }}>
        <div>Loading results...</div>
      </div>
    );
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
            <h1 style={{ color: '#1f2937', margin: 0 }}>FirstLot Dashboard</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: '#6b7280' }}>
              {client.company_name}
            </span>
            <button
              onClick={() => window.location.href = '/dashboard'}
              style={{
                backgroundColor: '#6b7280',
                color: 'white',
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>
      </header>

      <main style={{ padding: '2rem' }}>
        {results.length > 0 ? (
          <>
            {/* Summary Section */}
            <div style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '8px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              marginBottom: '2rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h2 style={{ color: '#1f2937', margin: 0 }}>Your COGS Reports</h2>
                <button
                  onClick={downloadAllResults}
                  style={{
                    backgroundColor: '#10b981',
                    color: 'white',
                    padding: '0.75rem 1.5rem',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Download All Results
                </button>
              </div>
              
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
                gap: '1rem' 
              }}>
                <StatCard title="Total Reports" value={results.length} />
                <StatCard title="Latest Report" value={formatTimestamp(results[0]?.timestamp)} />
                <StatCard title="Total SKUs Processed" value={results.reduce((sum, r) => sum + r.processed_skus, 0)} />
              </div>
            </div>

            {/* Results Table */}
            <div style={{
              backgroundColor: 'white',
              padding: '2rem',
              borderRadius: '8px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}>
              <h3 style={{ color: '#1f2937', marginBottom: '1.5rem' }}>Available Reports</h3>
              
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Date Processed</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>SKUs</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Total COGS</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Success Rate</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: '#374151' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((result, index) => (
                      <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '0.75rem', color: '#1f2937' }}>
                          {formatTimestamp(result.timestamp)}
                        </td>
                        <td style={{ padding: '0.75rem', color: '#6b7280' }}>
                          {result.processed_skus}
                        </td>
                        <td style={{ padding: '0.75rem', color: '#6b7280' }}>
                          ${result.total_cogs?.toFixed(2) || '0.00'}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            color: result.success_rate >= 100 ? '#059669' : '#d97706',
                            fontWeight: '500'
                          }}>
                            {result.success_rate?.toFixed(1) || '0'}%
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              onClick={() => viewResult(result)}
                              style={{
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                padding: '0.25rem 0.75rem',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer',
                                fontSize: '0.875rem'
                              }}
                            >
                              View
                            </button>
                            <button
                              onClick={() => downloadCSV(result)}
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
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          // No Results State
          <div style={{
            backgroundColor: 'white',
            padding: '3rem',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div>
            <h2 style={{ color: '#1f2937', marginBottom: '1rem' }}>No Reports Available</h2>
            <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
              You haven't processed any files yet. Upload your sales data to generate COGS reports.
            </p>
            <button
              onClick={() => window.location.href = '/upload'}
              style={{
                backgroundColor: '#3b82f6',
                color: 'white',
                padding: '0.75rem 1.5rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem'
              }}
            >
              Upload Files
            </button>
          </div>
        )}
      </main>

      {/* Modal for viewing result details */}
      {selectedResult && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            maxWidth: '500px',
            width: '90vw',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ color: '#1f2937', margin: 0 }}>Report Details</h3>
              <button
                onClick={closeModal}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#6b7280'
                }}
              >
                ×
              </button>
            </div>
            
            <ResultDetails result={selectedResult} />
            
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <button
                onClick={() => downloadCSV(selectedResult)}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  flex: 1
                }}
              >
                Download CSV
              </button>
              <button
                onClick={closeModal}
                style={{
                  backgroundColor: '#6b7280',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  flex: 1
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatCard = ({ title, value }) => (
  <div style={{
    padding: '1rem',
    backgroundColor: '#f9fafb',
    borderRadius: '4px',
    textAlign: 'center'
  }}>
    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1f2937' }}>
      {value}
    </div>
    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
      {title}
    </div>
  </div>
);

const ResultDetails = ({ result }) => (
  <div>
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        Processed Date
      </label>
      <div style={{ color: '#1f2937' }}>{formatTimestamp(result.timestamp)}</div>
    </div>
    
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        SKUs Processed
      </label>
      <div style={{ color: '#1f2937' }}>{result.processed_skus}</div>
    </div>
    
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        Total Units
      </label>
      <div style={{ color: '#1f2937' }}>{result.total_units || 0}</div>
    </div>
    
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        Total COGS
      </label>
      <div style={{ color: '#1f2937', fontSize: '1.25rem', fontWeight: 'bold' }}>
        ${result.total_cogs?.toFixed(2) || '0.00'}
      </div>
    </div>
    
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        Files Processed
      </label>
      <div style={{ color: '#1f2937' }}>
        Sales: {result.files?.sales || 0} rows, Lots: {result.files?.lots || 0} rows
      </div>
    </div>
    
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>
        Success Rate
      </label>
      <div style={{ 
        color: result.success_rate >= 100 ? '#059669' : '#d97706',
        fontWeight: 'bold'
      }}>
        {result.success_rate?.toFixed(1) || '0'}%
      </div>
    </div>
  </div>
);

// Helper functions
function formatTimestamp(timestamp) {
  if (!timestamp) return 'Unknown';
  const date = new Date(timestamp);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function generateCSVFromResult(result) {
  // Generate a detailed COGS report CSV
  const headers = [
    'Report_Date',
    'Client_ID', 
    'SKUs_Processed',
    'Total_Units',
    'Total_COGS',
    'Average_Cost_Per_Unit',
    'Success_Rate',
    'Sales_File_Rows',
    'Lots_File_Rows'
  ];
  
  const avgCostPerUnit = result.total_units > 0 ? (result.total_cogs / result.total_units) : 0;
  
  const row = [
    formatTimestamp(result.timestamp),
    result.client_id,
    result.processed_skus,
    result.total_units || 0,
    result.total_cogs?.toFixed(2) || '0.00',
    avgCostPerUnit.toFixed(4),
    result.success_rate?.toFixed(1) || '0',
    result.files?.sales || 0,
    result.files?.lots || 0
  ];
  
  return headers.join(',') + '\n' + row.join(',');
}

function generateCombinedCSV(results) {
  const headers = [
    'Report_Date',
    'Client_ID', 
    'SKUs_Processed',
    'Total_Units',
    'Total_COGS',
    'Average_Cost_Per_Unit',
    'Success_Rate',
    'Sales_File_Rows',
    'Lots_File_Rows'
  ];
  
  let csv = headers.join(',') + '\n';
  
  results.forEach(result => {
    const avgCostPerUnit = result.total_units > 0 ? (result.total_cogs / result.total_units) : 0;
    
    const row = [
      formatTimestamp(result.timestamp),
      result.client_id,
      result.processed_skus,
      result.total_units || 0,
      result.total_cogs?.toFixed(2) || '0.00',
      avgCostPerUnit.toFixed(4),
      result.success_rate?.toFixed(1) || '0',
      result.files?.sales || 0,
      result.files?.lots || 0
    ];
    
    csv += row.join(',') + '\n';
  });
  
  return csv;
}

export default DownloadPage;