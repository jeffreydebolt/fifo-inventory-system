import React, { useState } from 'react';
import { useClient } from '../contexts/ClientContext';
// import { API_BASE } from '../lib/config';
const API_BASE = 'https://api.firstlot.co';

export default function UploadPage() {
  const { client } = useClient();
  const [lotsFile, setLotsFile] = useState(null);
  const [salesFile, setSalesFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState('');
  const [progress, setProgress] = useState({ step: 1, total: 3 });

  const onPick = (setter) => (e) => setter(e.target.files?.[0] ?? null);

  async function uploadCSV(url, file) {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('tenant_id', 'test_user_9999'); // Test tenant - NOT your real data
    const res = await fetch(url, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  const doUploadLots = async () => {
    if (!lotsFile) return setMsg('Pick a lots CSV first.');
    setProcessing(true); 
    setMsg('Uploading lots…');
    setProgress({ step: 2, total: 3 });
    try { 
      await uploadCSV(`${API_BASE}/api/v1/files/lots`, lotsFile); 
      setMsg('✅ Lots uploaded successfully'); 
      setProgress({ step: 3, total: 3 });
    }
    catch (e) { setMsg(`❌ Lots upload failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  const doUploadSales = async () => {
    if (!salesFile) return setMsg('Pick a sales CSV first.');
    setProcessing(true); 
    setMsg('Uploading sales…');
    setProgress({ step: 2, total: 3 });
    try { 
      await uploadCSV(`${API_BASE}/api/v1/files/sales`, salesFile); 
      setMsg('✅ Sales uploaded successfully'); 
      setProgress({ step: 3, total: 3 });
    }
    catch (e) { setMsg(`❌ Sales upload failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  const doProcessSalesOnly = async () => {
    if (!salesFile) return setMsg('Pick a sales CSV first.');
    setProcessing(true); 
    setMsg('Processing sales against existing inventory…');
    setProgress({ step: 2, total: 3 });
    try { 
      await uploadCSV(`${API_BASE}/api/v1/runs`, salesFile); 
      setMsg('✅ COGS calculation completed successfully'); 
      setProgress({ step: 3, total: 3 });
    }
    catch (e) { setMsg(`❌ Processing failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  const downloadTemplate = async (type) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/files/templates/${type}`);
      const csv = await response.text();
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_template.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setMsg(`❌ Failed to download template: ${e.message}`);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--gray-50)' }}>
      {/* Modern Header */}
      <header className="shadow-sm" style={{
        backgroundColor: 'white',
        padding: '1rem 2rem',
        borderBottom: '1px solid var(--gray-200)'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1200px',
          margin: '0 auto'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              backgroundColor: 'var(--success-500)',
              color: 'white',
              padding: '0.75rem',
              borderRadius: '0.5rem',
              fontWeight: 'bold',
              fontSize: '1rem',
              boxShadow: 'var(--shadow)'
            }}>
              FL
            </div>
            <div>
              <h1 style={{ 
                color: 'var(--gray-900)', 
                margin: 0, 
                fontSize: '1.5rem',
                fontWeight: '700'
              }}>FirstLot FIFO</h1>
              <span style={{ 
                color: 'var(--gray-500)', 
                fontSize: '0.875rem',
                fontWeight: '500'
              }}>Upload & Process COGS</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div className="status-indicator status-success">
              Client: {client.client_id}
            </div>
          </div>
        </div>
      </header>

      <main style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Process Overview with Progress */}
        <div className="card fade-in" style={{
          background: 'linear-gradient(135deg, var(--primary-500) 0%, var(--success-500) 100%)',
          color: 'white',
          marginBottom: '2rem',
          textAlign: 'center',
          border: 'none'
        }}>
          <h2 style={{ 
            color: 'white', 
            marginBottom: '1rem', 
            fontSize: '1.75rem',
            fontWeight: '700'
          }}>FIFO Processing Pipeline</h2>
          <p style={{ 
            color: 'rgba(255,255,255,0.9)', 
            marginBottom: '2rem',
            fontSize: '1rem'
          }}>Upload your data and calculate COGS using First-In-First-Out methodology</p>
          
          {/* Progress Steps */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            gap: '1.5rem', 
            fontSize: '0.875rem',
            marginBottom: '1rem'
          }}>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              gap: '0.5rem',
              opacity: lotsFile ? 1 : 0.7,
              transition: 'opacity 0.3s ease'
            }}>
              <div style={{
                backgroundColor: lotsFile ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.1)',
                padding: '0.75rem',
                borderRadius: '50%',
                fontSize: '1.25rem'
              }}>📦</div>
              <span style={{ fontWeight: '600' }}>Upload Lots</span>
            </div>
            <div style={{ fontSize: '1.5rem', opacity: 0.7 }}>→</div>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              gap: '0.5rem',
              opacity: salesFile ? 1 : 0.7,
              transition: 'opacity 0.3s ease'
            }}>
              <div style={{
                backgroundColor: salesFile ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.1)',
                padding: '0.75rem',
                borderRadius: '50%',
                fontSize: '1.25rem'
              }}>📊</div>
              <span style={{ fontWeight: '600' }}>Upload Sales</span>
            </div>
            <div style={{ fontSize: '1.5rem', opacity: 0.7 }}>→</div>
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              gap: '0.5rem',
              opacity: (lotsFile && salesFile) ? 1 : 0.7,
              transition: 'opacity 0.3s ease'
            }}>
              <div style={{
                backgroundColor: (lotsFile && salesFile) ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.1)',
                padding: '0.75rem',
                borderRadius: '50%',
                fontSize: '1.25rem'
              }}>⚙️</div>
              <span style={{ fontWeight: '600' }}>Calculate COGS</span>
            </div>
          </div>
          
          {/* Progress Bar */}
          {processing && (
            <div className="progress-bar fade-in" style={{ marginTop: '1rem' }}>
              <div 
                className="progress-fill" 
                style={{ width: `${(progress.step / progress.total) * 100}%` }}
              />
            </div>
          )}
        </div>

        {/* File Upload Section */}
        <div className="card fade-in" style={{ marginBottom: '2rem' }}>
          <h3 style={{ 
            color: 'var(--gray-900)', 
            marginBottom: '1.5rem', 
            fontSize: '1.25rem',
            fontWeight: '600'
          }}>Upload Files</h3>
          
          <div className="grid-responsive" style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '2rem', 
            marginBottom: '2rem' 
          }}>
            
            {/* Purchase Lots Upload */}
            <div className={`upload-area ${lotsFile ? 'has-file' : ''}`}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📦</div>
              <h4 style={{ 
                color: 'var(--gray-900)', 
                marginBottom: '0.5rem',
                fontSize: '1.125rem',
                fontWeight: '600'
              }}>Purchase Lots</h4>
              <p style={{ 
                color: 'var(--gray-600)', 
                fontSize: '0.875rem', 
                marginBottom: '1rem',
                lineHeight: '1.4'
              }}>
                Upload inventory purchase data with costs and dates
              </p>
              <div className="status-indicator" style={{ 
                backgroundColor: 'var(--primary-100)',
                color: 'var(--primary-700)',
                marginBottom: '1.5rem',
                fontSize: '0.75rem'
              }}>
                Required: lot_id, sku, received_date, original_quantity, remaining_quantity, unit_price, freight_cost_per_unit
              </div>
              
              <input
                type="file"
                accept=".csv"
                onChange={onPick(setLotsFile)}
                style={{ display: 'none' }}
                id="lots-upload"
                disabled={processing}
              />
              
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                <label
                  htmlFor="lots-upload"
                  className={`btn ${lotsFile ? 'btn-success' : 'btn-primary'}`}
                  style={{
                    cursor: processing ? 'not-allowed' : 'pointer',
                    opacity: processing ? 0.6 : 1,
                    fontSize: '0.875rem',
                    gap: '0.5rem'
                  }}
                >
                  {lotsFile ? (
                    <>
                      <span>✓</span>
                      <span>{lotsFile.name}</span>
                    </>
                  ) : (
                    <>
                      <span>📁</span>
                      <span>Choose CSV File</span>
                    </>
                  )}
                </label>
                <button
                  type="button"
                  onClick={() => downloadTemplate('lots')}
                  className="btn"
                  style={{
                    backgroundColor: 'var(--gray-600)',
                    color: 'white',
                    fontSize: '0.75rem',
                    padding: '0.5rem 1rem',
                    gap: '0.25rem'
                  }}
                >
                  <span>📥</span>
                  <span>Template</span>
                </button>
              </div>
            </div>

            {/* Sales Upload */}
            <div className={`upload-area ${salesFile ? 'has-file' : ''}`}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📊</div>
              <h4 style={{ 
                color: 'var(--gray-900)', 
                marginBottom: '0.5rem',
                fontSize: '1.125rem',
                fontWeight: '600'
              }}>Sales Data</h4>
              <p style={{ 
                color: 'var(--gray-600)', 
                fontSize: '0.875rem', 
                marginBottom: '1rem',
                lineHeight: '1.4'
              }}>
                Upload monthly sales data for COGS calculation
              </p>
              <div className="status-indicator" style={{ 
                backgroundColor: 'var(--warning-100)',
                color: 'var(--warning-700)',
                marginBottom: '1.5rem',
                fontSize: '0.75rem'
              }}>
                Required: sku, units moved, Month
              </div>
              
              <input
                type="file"
                accept=".csv"
                onChange={onPick(setSalesFile)}
                style={{ display: 'none' }}
                id="sales-upload"
                disabled={processing}
              />
              
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                <label
                  htmlFor="sales-upload"
                  className={`btn ${salesFile ? 'btn-success' : 'btn-primary'}`}
                  style={{
                    cursor: processing ? 'not-allowed' : 'pointer',
                    opacity: processing ? 0.6 : 1,
                    fontSize: '0.875rem',
                    gap: '0.5rem'
                  }}
                >
                  {salesFile ? (
                    <>
                      <span>✓</span>
                      <span>{salesFile.name}</span>
                    </>
                  ) : (
                    <>
                      <span>📁</span>
                      <span>Choose CSV File</span>
                    </>
                  )}
                </label>
                <button
                  type="button"
                  onClick={() => downloadTemplate('sales')}
                  className="btn"
                  style={{
                    backgroundColor: 'var(--gray-600)',
                    color: 'white',
                    fontSize: '0.75rem',
                    padding: '0.5rem 1rem',
                    gap: '0.25rem'
                  }}
                >
                  <span>📥</span>
                  <span>Template</span>
                </button>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="grid-responsive" style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
            gap: '1rem'
          }}>
            <button
              className={`btn ${(!lotsFile || processing) ? '' : 'btn-primary'}`}
              onClick={doUploadLots}
              disabled={!lotsFile || processing}
              style={{
                backgroundColor: (!lotsFile || processing) ? 'var(--gray-400)' : undefined,
                cursor: (!lotsFile || processing) ? 'not-allowed' : 'pointer',
                gap: '0.5rem',
                justifyContent: 'center'
              }}
            >
              {processing ? (
                <>
                  <span className="pulse">⏳</span>
                  <span>Uploading...</span>
                </>
              ) : !lotsFile ? (
                <>
                  <span>📦</span>
                  <span>Select Lots File First</span>
                </>
              ) : (
                <>
                  <span>📦</span>
                  <span>Upload Lots Only</span>
                </>
              )}
            </button>

            <button
              className={`btn ${(!salesFile || processing) ? '' : 'btn-warning'}`}
              onClick={doUploadSales}
              disabled={!salesFile || processing}
              style={{
                backgroundColor: (!salesFile || processing) ? 'var(--gray-400)' : undefined,
                cursor: (!salesFile || processing) ? 'not-allowed' : 'pointer',
                gap: '0.5rem',
                justifyContent: 'center'
              }}
            >
              {processing ? (
                <>
                  <span className="pulse">⏳</span>
                  <span>Uploading...</span>
                </>
              ) : !salesFile ? (
                <>
                  <span>📊</span>
                  <span>Select Sales File First</span>
                </>
              ) : (
                <>
                  <span>💰</span>
                  <span>Upload Sales Only</span>
                </>
              )}
            </button>

            <button
              className={`btn ${(!salesFile || processing) ? '' : 'btn-success'}`}
              onClick={doProcessSalesOnly}
              disabled={!salesFile || processing}
              style={{
                backgroundColor: (!salesFile || processing) ? 'var(--gray-400)' : undefined,
                cursor: (!salesFile || processing) ? 'not-allowed' : 'pointer',
                gap: '0.5rem',
                justifyContent: 'center'
              }}
            >
              {processing ? (
                <>
                  <span className="pulse">⚙️</span>
                  <span>Processing...</span>
                </>
              ) : !salesFile ? (
                <>
                  <span>🚀</span>
                  <span>Need Sales File</span>
                </>
              ) : (
                <>
                  <span>🚀</span>
                  <span>Process vs Inventory</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Status Messages */}
        {msg && (
          <div className={`card fade-in ${msg.includes('✅') ? 'status-success' : 'status-error'}`} style={{
            backgroundColor: msg.includes('✅') ? '#f0fdf4' : '#fef2f2',
            border: `2px solid ${msg.includes('✅') ? 'var(--success-500)' : 'var(--error-500)'}`,
            color: msg.includes('✅') ? 'var(--success-700)' : 'var(--error-700)',
            textAlign: 'center',
            fontSize: '1rem',
            fontWeight: '600'
          }}>
            <div style={{ 
              fontSize: '2rem', 
              marginBottom: '0.5rem' 
            }}>
              {msg.includes('✅') ? '✅' : '❌'}
            </div>
            <p style={{ margin: 0 }}>{msg.replace(/[✅❌]\s*/, '')}</p>
          </div>
        )}
      </main>
    </div>
  );
}