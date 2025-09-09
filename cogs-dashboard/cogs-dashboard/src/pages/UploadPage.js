import React, { useState } from 'react';
import { useClient } from '../contexts/ClientContext';
import { API_BASE } from '../lib/config';

export default function UploadPage() {
  const { client } = useClient();
  const [lotsFile, setLotsFile] = useState(null);
  const [salesFile, setSalesFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [msg, setMsg] = useState('');

  const onPick = (setter) => (e) => setter(e.target.files?.[0] ?? null);

  async function uploadCSV(url, file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(url, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${await res.text()}`);
    return res.json();
  }

  const lotsUrl    = `${API_BASE}/api/v1/runs/upload/lots?tenant_id=${client.client_id}`;
  const salesUrl   = `${API_BASE}/api/v1/runs/upload/sales?tenant_id=${client.client_id}`;
  const processUrl = `${API_BASE}/api/v1/runs/process/sales?tenant_id=${client.client_id}`;

  const doUploadLots = async () => {
    if (!lotsFile) return setMsg('Pick a lots CSV first.');
    setProcessing(true); setMsg('Uploading lots…');
    try { await uploadCSV(lotsUrl, lotsFile); setMsg('✅ Lots uploaded.'); }
    catch (e) { setMsg(`❌ Lots upload failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  const doUploadSales = async () => {
    if (!salesFile) return setMsg('Pick a sales CSV first.');
    setProcessing(true); setMsg('Uploading sales…');
    try { await uploadCSV(salesUrl, salesFile); setMsg('✅ Sales uploaded.'); }
    catch (e) { setMsg(`❌ Sales upload failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  const doProcessSalesOnly = async () => {
    if (!salesFile) return setMsg('Pick a sales CSV first.');
    setProcessing(true); setMsg('Processing sales against existing inventory…');
    try { await uploadCSV(processUrl, salesFile); setMsg('✅ Processed sales vs existing inventory.'); }
    catch (e) { setMsg(`❌ Processing failed: ${e.message}`); }
    finally { setProcessing(false); }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: 'white', marginBottom: 16, fontSize: 24 }}>
        FIFO Processing Pipeline — v9
      </h2>

      <div style={{ display: 'grid', gap: 24, maxWidth: 720 }}>
        <section style={{ background: '#111827', padding: 16, borderRadius: 12 }}>
          <h3 style={{ color: 'white', marginBottom: 8 }}>📦 Purchase Lots</h3>
          <input type="file" accept=".csv" onChange={onPick(setLotsFile)} />
          <div style={{ marginTop: 8, color: '#9CA3AF' }}>
            {lotsFile ? lotsFile.name : 'No file selected'}
          </div>
          <button onClick={doUploadLots} disabled={!lotsFile || processing} style={{ marginTop: 12 }}>
            {processing ? '⏳ Uploading…' : '📦 Upload Lots Only'}
          </button>
        </section>

        <section style={{ background: '#111827', padding: 16, borderRadius: 12 }}>
          <h3 style={{ color: 'white', marginBottom: 8 }}>💰 Sales Data</h3>
          <input type="file" accept=".csv" onChange={onPick(setSalesFile)} />
          <div style={{ marginTop: 8, color: '#9CA3AF' }}>
            {salesFile ? salesFile.name : 'No file selected'}
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
            <button onClick={doUploadSales} disabled={!salesFile || processing}>
              {processing ? '⏳ Uploading…' : '💰 Upload Sales Only'}
            </button>
            <button onClick={doProcessSalesOnly} disabled={!salesFile || processing}>
              {processing ? '⏳ Processing…' : '🚀 Process Sales vs Existing Inventory'}
            </button>
          </div>
        </section>

        {msg && <div style={{ color: 'white' }}>{msg}</div>}
      </div>
    </div>
  );
}