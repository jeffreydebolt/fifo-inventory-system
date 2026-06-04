import React from 'react';
import { demoRun } from '../demoData';

const sectionStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
  marginBottom: '1.5rem',
  overflow: 'hidden'
};

const headerStyle = {
  padding: '1rem 1.25rem',
  borderBottom: '1px solid #e5e7eb',
  background: '#f9fafb'
};

const tableStyle = {
  borderCollapse: 'collapse',
  width: '100%',
  fontSize: '0.875rem'
};

const cellStyle = {
  borderBottom: '1px solid #f3f4f6',
  padding: '0.75rem',
  textAlign: 'left',
  verticalAlign: 'top'
};

function titleize(key) {
  return key.replaceAll('_', ' ');
}

function DemoTable({ title, rows, emptyText }) {
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return (
    <section style={sectionStyle}>
      <div style={headerStyle}>
        <h2 style={{ margin: 0, fontSize: '1.125rem' }}>{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p style={{ padding: '1rem', margin: 0 }}>{emptyText || 'No rows.'}</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} style={{ ...cellStyle, background: '#f9fafb', fontWeight: 700 }}>
                    {titleize(column)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td key={column} style={cellStyle}>{row[column]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function DownloadLink({ sectionName, rows }) {
  const href = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(rows, null, 2))}`;
  return (
    <a
      href={href}
      download={`${sectionName}.json`}
      style={{ color: '#2563eb', fontWeight: 600, marginRight: '1rem' }}
    >
      Download {sectionName}.json
    </a>
  );
}

export default function DemoPage() {
  return (
    <main style={{ minHeight: '100vh', background: '#f3f4f6', padding: '2rem' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{ ...sectionStyle, padding: '1.5rem', borderColor: '#16a34a' }}>
          <div style={{
            display: 'inline-block',
            background: '#dcfce7',
            color: '#166534',
            fontWeight: 700,
            borderRadius: '999px',
            padding: '0.35rem 0.75rem',
            marginBottom: '1rem'
          }}>
            {demoRun.safetyMode}
          </div>
          <h1 style={{ margin: '0 0 0.5rem' }}>FirstLot local MVP demo</h1>
          <p style={{ margin: '0 0 1rem', color: '#4b5563' }}>
            Static fixture review of purchase lots CSV + movement CSV → local FIFO outputs. Generated at {demoRun.generatedAt}.
          </p>
          <ul style={{ margin: 0, color: '#4b5563' }}>
            <li>Purchase lots: <code>{demoRun.inputs.purchaseLots}</code></li>
            <li>Movement/sales: <code>{demoRun.inputs.movement}</code></li>
            <li>Checked-in output artifacts: <code>{demoRun.inputs.artifactDirectory}</code></li>
          </ul>
        </div>

        <section style={{ ...sectionStyle, padding: '1rem 1.25rem' }}>
          <h2 style={{ marginTop: 0 }}>Exports</h2>
          <DownloadLink sectionName="cogs_summary" rows={demoRun.cogsSummary} />
          <DownloadLink sectionName="remaining_layers" rows={demoRun.remainingLayers} />
          <DownloadLink sectionName="audit_trail" rows={demoRun.auditTrail} />
          <DownloadLink sectionName="shortfalls" rows={demoRun.shortfalls} />
        </section>

        <DemoTable title="COGS summary" rows={demoRun.cogsSummary} />
        <DemoTable title="Remaining layers" rows={demoRun.remainingLayers} />
        <DemoTable title="Shortfalls / exceptions" rows={demoRun.shortfalls} emptyText="No shortfalls." />
        <DemoTable title="Audit trail" rows={demoRun.auditTrail} />
      </div>
    </main>
  );
}
