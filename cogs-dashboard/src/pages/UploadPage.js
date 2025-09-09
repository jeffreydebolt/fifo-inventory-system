import React, { useState } from 'react';
import { useClient } from '../contexts/ClientContext';

const UploadPage = () => {
  const { client } = useClient();
  const [lotsFile, setLotsFile] = useState(null);
  const [salesFile, setSalesFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState({ lots: null, sales: null });

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const handleFileChange = (type, event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.csv')) {
      setError(`Please select a CSV file for ${type}`);
      return;
    }

    if (type === 'lots') {
      setLotsFile(file);
      setUploadProgress(prev => ({ ...prev, lots: null }));
    } else if (type === 'sales') {
      setSalesFile(file);
      setUploadProgress(prev => ({ ...prev, sales: null }));
    }
    setError('');
    setResult(null);
  };

  const uploadFile = async (file, type) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tenant_id', client.client_id);

    const response = await fetch(`${API_BASE}/api/v1/files/${type}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Failed to upload ${type} file`);
    }

    return await response.json();
  };

  const uploadLots = async () => {
    if (!lotsFile) {
      setError('Please select a lots file');
      return;
    }

    setProcessing(true);
    setError('');
    setUploadProgress({ lots: 'uploading', sales: null });

    try {
      const lotsResult = await uploadFile(lotsFile, 'lots');
      setUploadProgress({ lots: 'uploaded', sales: null });
      setResult({ message: 'Lots file uploaded successfully!', file_id: lotsResult.file_id });
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
      setUploadProgress({ lots: 'error', sales: null });
    } finally {
      setProcessing(false);
    }
  };

  const uploadSales = async () => {
    if (!salesFile) {
      setError('Please select a sales file');
      return;
    }

    setProcessing(true);
    setError('');
    setUploadProgress({ lots: null, sales: 'uploading' });

    try {
      const salesResult = await uploadFile(salesFile, 'sales');
      setUploadProgress({ lots: null, sales: 'uploaded' });
      setResult({ message: 'Sales file uploaded successfully!', file_id: salesResult.file_id });
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
      setUploadProgress({ lots: null, sales: 'error' });
    } finally {
      setProcessing(false);
    }
  };

  const processSalesOnly = async () => {
    if (!salesFile) {
      setError('Please select a sales file');
      return;
    }

    setProcessing(true);
    setError('');
    setResult(null);
    setUploadProgress({ lots: null, sales: 'processing' });

    try {
      // Upload sales file
      const salesResult = await uploadFile(salesFile, 'sales');
      
      // Process FIFO with existing inventory (no lots file)
      const runResponse = await fetch(`${API_BASE}/api/v1/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: client.client_id,
          sales_file_id: salesResult.file_id
          // Note: no lots_file_id - uses existing inventory
        })
      });

      if (!runResponse.ok) {
        const errorData = await runResponse.json();
        throw new Error(errorData.detail || 'Failed to process FIFO calculation');
      }

      const runResult = await runResponse.json();
      
      setUploadProgress({ lots: null, sales: 'completed' });
      setResult({
        run_id: runResult.run_id,
        total_sales_processed: runResult.total_sales_processed,
        total_cogs_calculated: runResult.total_cogs_calculated,
        processed_skus: runResult.processed_skus,
        unmatched_sales_count: runResult.unmatched_sales_count || 0,
        warning: runResult.warning
      });

    } catch (err) {
      setError(`Processing failed: ${err.message}`);
      setUploadProgress({ lots: null, sales: 'error' });
    } finally {
      setProcessing(false);
    }
  };

  const downloadTemplate = async (type) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/files/templates/${type}`);
      if (!response.ok) throw new Error('Failed to download template');
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(`Failed to download ${type} template: ${err.message}`);
    }
  };

  const getProgressIcon = (status) => {
    switch (status) {
      case 'uploading': return '⏫';
      case 'uploaded': return '✅';
      case 'processing': return '⚙️';
      case 'completed': return '🎉';
      default: return '';
    }
  };

  const getProgressText = (status) => {
    switch (status) {
      case 'uploading': return 'Uploading...';
      case 'uploaded': return 'Uploaded';
      case 'processing': return 'Processing...';
      case 'completed': return 'Complete';
      default: return '';
    }
  };

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
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Upload & Process</span>
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
              ← Dashboard
            </button>
          </div>
        </div>
      </header>

      <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Process Overview */}
        <div style={{
          backgroundColor: '#10b981',
          color: 'white',
          padding: '1.5rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          textAlign: 'center'
        }}>
          <h2 style={{ color: 'white', marginBottom: '1rem', fontSize: '1.5rem' }}>FIFO Processing Pipeline — v5 SEPARATE UPLOADS FIXED</h2>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '2rem', fontSize: '0.875rem' }}>
            <div style={{ opacity: (lotsFile && uploadProgress.lots) ? 1 : 0.7 }}>
              {getProgressIcon(uploadProgress.lots)} Upload Lots
            </div>
            <span>→</span>
            <div style={{ opacity: (salesFile && uploadProgress.sales) ? 1 : 0.7 }}>
              {getProgressIcon(uploadProgress.sales)} Upload Sales
            </div>
            <span>→</span>
            <div style={{ opacity: (uploadProgress.lots === 'processing' || result) ? 1 : 0.7 }}>
              {result ? '🎉' : '⚙️'} Calculate COGS
            </div>
          </div>
        </div>

        {/* File Upload Section */}
        <div style={{
          backgroundColor: 'white',
          padding: '2rem',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          marginBottom: '2rem'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
            
            {/* Purchase Lots Upload */}
            <div style={{
              border: `2px dashed ${lotsFile ? '#10b981' : '#d1d5db'}`,
              borderRadius: '8px',
              padding: '2rem',
              textAlign: 'center',
              backgroundColor: lotsFile ? '#f0fdf4' : '#fafafa',
              position: 'relative'
            }}>
              {uploadProgress.lots && (
                <div style={{
                  position: 'absolute',
                  top: '0.5rem',
                  right: '0.5rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem'
                }}>
                  {getProgressText(uploadProgress.lots)}
                </div>
              )}
              
              <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📦</div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>Purchase Lots</h3>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '1rem' }}>
                Inventory purchases with costs
              </p>
              <div style={{ color: '#10b981', fontSize: '0.75rem', marginBottom: '1rem' }}>
                Format: PO#, SKU, Date, Quantity, Cost
              </div>
              
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange('lots', e)}
                style={{ display: 'none' }}
                id="lots-upload"
                disabled={processing}
              />
              
              <label
                htmlFor="lots-upload"
                style={{
                  display: 'inline-block',
                  backgroundColor: lotsFile ? '#10b981' : '#3b82f6',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '4px',
                  cursor: processing ? 'not-allowed' : 'pointer',
                  marginBottom: '1rem',
                  opacity: processing ? 0.6 : 1
                }}
              >
                {lotsFile ? `✓ ${lotsFile.name}` : 'Choose CSV File'}
              </label>
              
              <div>
                <button
                  onClick={() => downloadTemplate('lots')}
                  disabled={processing}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#10b981',
                    padding: '0.5rem',
                    border: 'none',
                    cursor: processing ? 'not-allowed' : 'pointer',
                    fontSize: '0.875rem',
                    textDecoration: 'underline',
                    opacity: processing ? 0.6 : 1
                  }}
                >
                  Download Template →
                </button>
              </div>
            </div>

            {/* Sales Upload */}
            <div style={{
              border: `2px dashed ${salesFile ? '#10b981' : '#d1d5db'}`,
              borderRadius: '8px',
              padding: '2rem',
              textAlign: 'center',
              backgroundColor: salesFile ? '#f0fdf4' : '#fafafa',
              position: 'relative'
            }}>
              {uploadProgress.sales && (
                <div style={{
                  position: 'absolute',
                  top: '0.5rem',
                  right: '0.5rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.25rem 0.5rem',
                  borderRadius: '4px',
                  fontSize: '0.75rem'
                }}>
                  {getProgressText(uploadProgress.sales)}
                </div>
              )}
              
              <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📊</div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>Sales Data</h3>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '1rem' }}>
                Monthly sales by SKU
              </p>
              <div style={{ color: '#10b981', fontSize: '0.75rem', marginBottom: '1rem' }}>
                Format: SKU, Quantity, Month
              </div>
              
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileChange('sales', e)}
                style={{ display: 'none' }}
                id="sales-upload"
                disabled={processing}
              />
              
              <label
                htmlFor="sales-upload"
                style={{
                  display: 'inline-block',
                  backgroundColor: salesFile ? '#10b981' : '#3b82f6',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '4px',
                  cursor: processing ? 'not-allowed' : 'pointer',
                  marginBottom: '1rem',
                  opacity: processing ? 0.6 : 1
                }}
              >
                {salesFile ? `✓ ${salesFile.name}` : 'Choose CSV File'}
              </label>
              
              <div>
                <button
                  onClick={() => downloadTemplate('sales')}
                  disabled={processing}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#10b981',
                    padding: '0.5rem',
                    border: 'none',
                    cursor: processing ? 'not-allowed' : 'pointer',
                    fontSize: '0.875rem',
                    textDecoration: 'underline',
                    opacity: processing ? 0.6 : 1
                  }}
                >
                  Download Template →
                </button>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', textAlign: 'center' }}>
            <button
              onClick={uploadLots}
              disabled={!lotsFile || processing}
              style={{
                backgroundColor: (!lotsFile || processing) ? '#9ca3af' : '#3b82f6',
                color: 'white',
                padding: '1rem 2rem',
                border: 'none',
                borderRadius: '8px',
                cursor: (!lotsFile || processing) ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: '600'
              }}
            >
              {processing ? '⏳ Uploading...' : 
               !lotsFile ? 'Select Lots File' :
               '📦 Upload Lots Only'}
            </button>

            <button
              onClick={uploadSales}
              disabled={!salesFile || processing}
              style={{
                backgroundColor: (!salesFile || processing) ? '#9ca3af' : '#f59e0b',
                color: 'white',
                padding: '1rem 2rem',
                border: 'none',
                borderRadius: '8px',
                cursor: (!salesFile || processing) ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: '600'
              }}
            >
              {processing ? '⏳ Uploading...' : 
               !salesFile ? 'Select Sales File' :
               '💰 Upload Sales Only'}
            </button>

            <button
              onClick={processSalesOnly}
              disabled={!salesFile || processing}
              style={{
                backgroundColor: (!salesFile || processing) ? '#9ca3af' : '#10b981',
                color: 'white',
                padding: '1rem 2rem',
                border: 'none',
                borderRadius: '8px',
                cursor: (!salesFile || processing) ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: '600'
              }}
            >
              {processing ? '⏳ Processing...' : 
               !salesFile ? 'Need Sales File' :
               '🚀 Process Sales vs Existing Inventory'}
            </button>
            
            <div style={{ marginTop: '1rem', textAlign: 'center' }}>
              <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                Upload lots and sales separately, or process sales against existing inventory
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fca5a5',
            color: '#dc2626',
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '2rem'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>⚠️ Error</h3>
            <p style={{ margin: 0 }}>{error}</p>
          </div>
        )}

        {/* Success Results */}
        {result && (
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            <h2 style={{ color: '#0f172a', marginBottom: '1.5rem' }}>✅ FIFO Processing Complete!</h2>
            
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
              gap: '1rem',
              marginBottom: '2rem'
            }}>
              <StatCard title="Run ID" value={result.run_id} />
              <StatCard title="Sales Records" value={result.total_sales_processed} />
              <StatCard title="Lots Records" value={result.lots_uploaded} />
              <StatCard title="Total COGS" value={`$${result.total_cogs_calculated?.toFixed(2) || '0.00'}`} />
            </div>

            <div style={{
              backgroundColor: '#f0fdf4',
              border: '1px solid #10b981',
              padding: '1rem',
              borderRadius: '4px',
              marginBottom: '1rem'
            }}>
              <p style={{ margin: 0, color: '#374151' }}>
                🎉 Your FIFO calculation has been completed successfully! 
                You can now view your lot history and monthly COGS reports.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={() => window.location.href = '/lot-history'}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                View Lot History
              </button>
              <button
                onClick={() => window.location.href = '/monthly-cogs'}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '0.75rem 1.5rem',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '1rem'
                }}
              >
                View Monthly COGS
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const StatCard = ({ title, value }) => (
  <div style={{
    padding: '1rem',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    textAlign: 'center'
  }}>
    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#0f172a' }}>
      {value}
    </div>
    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.25rem' }}>
      {title}
    </div>
  </div>
);

export default UploadPage;