import React from 'react';
import { demoRun } from '../demoData';

const page = {
  minHeight: '100vh',
  background: '#f8fafc',
  color: '#111827',
  padding: '2rem'
};

const shell = { maxWidth: '1040px', margin: '0 auto' };

const card = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '16px',
  boxShadow: '0 12px 30px rgba(15, 23, 42, 0.06)'
};

const grid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '1rem'
};

const tableStyle = {
  borderCollapse: 'collapse',
  width: '100%',
  fontSize: '0.92rem'
};

const cellStyle = {
  borderBottom: '1px solid #e5e7eb',
  padding: '0.8rem',
  textAlign: 'left'
};

const fixtureCostBreakdown = {
  'SKU-A': {
    merchandiseCost: 196,
    shippingCost: 14
  },
  'SKU-B': {
    merchandiseCost: 40,
    shippingCost: 0
  }
};

function money(value) {
  return Number(value).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function number(value) {
  return Number(value).toLocaleString('en-US');
}

function cogsRows() {
  return demoRun.cogsSummary.map((row) => {
    const unitsSold = Number(row.total_quantity_sold);
    const totalCost = Number(row.total_cogs);
    const breakdown = fixtureCostBreakdown[row.sku] || {
      merchandiseCost: totalCost,
      shippingCost: 0
    };

    return {
      sku: row.sku,
      unitsSold,
      unitCost: breakdown.merchandiseCost / unitsSold,
      shippingCost: breakdown.shippingCost,
      totalCost,
      averageCost: totalCost / unitsSold
    };
  });
}

function Pill({ children }) {
  return (
    <span style={{
      display: 'inline-flex',
      background: '#dcfce7',
      color: '#166534',
      fontWeight: 800,
      borderRadius: '999px',
      padding: '0.35rem 0.7rem',
      fontSize: '0.82rem'
    }}>
      {children}
    </span>
  );
}

function StepCard({ number: stepNumber, title, body }) {
  return (
    <div style={{ ...card, padding: '1rem' }}>
      <div style={{
        width: '2rem',
        height: '2rem',
        display: 'grid',
        placeItems: 'center',
        borderRadius: '0.65rem',
        background: '#111827',
        color: 'white',
        fontWeight: 900,
        marginBottom: '0.75rem'
      }}>{stepNumber}</div>
      <h3 style={{ margin: '0 0 0.4rem', fontSize: '1rem' }}>{title}</h3>
      <p style={{ margin: 0, color: '#4b5563', lineHeight: 1.45 }}>{body}</p>
    </div>
  );
}

function DownloadCsvLink({ rows }) {
  const csv = [
    ['SKU', 'Units Sold', 'Unit Cost', 'Shipping Cost', 'Total Cost', 'Average Cost'].join(','),
    ...rows.map((row) => [
      row.sku,
      row.unitsSold,
      row.unitCost.toFixed(2),
      row.shippingCost.toFixed(2),
      row.totalCost.toFixed(2),
      row.averageCost.toFixed(2)
    ].join(','))
  ].join('\n');

  return (
    <a
      href={`data:text/csv;charset=utf-8,${encodeURIComponent(csv)}`}
      download="firstlot_monthly_cogs_results.csv"
      style={{
        background: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: '0.85rem',
        color: '#1d4ed8',
        display: 'inline-flex',
        fontWeight: 800,
        padding: '0.75rem 0.9rem',
        textDecoration: 'none'
      }}
    >
      Download results CSV
    </a>
  );
}

function Shortfalls() {
  if (demoRun.shortfalls.length === 0) {
    return <p style={{ margin: 0, color: '#166534' }}>No unmatched or shortfall rows in this fixture run.</p>;
  }

  return (
    <div style={{ display: 'grid', gap: '0.65rem' }}>
      {demoRun.shortfalls.map((row) => (
        <div key={`${row.sale_id}-${row.sku}`} style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '0.9rem', padding: '0.85rem' }}>
          <strong>{row.sku}</strong>: sale {row.sale_id} requested {row.requested_quantity}, allocated {row.allocated_quantity}, short {row.shortfall_quantity}.
        </div>
      ))}
    </div>
  );
}

export default function DemoPage() {
  const rows = cogsRows();
  const totalCogs = rows.reduce((sum, row) => sum + row.totalCost, 0);
  const unitsSold = rows.reduce((sum, row) => sum + row.unitsSold, 0);

  return (
    <main style={page}>
      <div style={shell}>
        <section style={{ ...card, padding: '1.5rem', marginBottom: '1rem' }}>
          <Pill>{demoRun.safetyMode}</Pill>
          <h1 style={{ margin: '1rem 0 0.5rem', fontSize: 'clamp(2rem, 4vw, 3rem)' }}>FirstLot FIFO COGS</h1>
          <p style={{ margin: 0, color: '#475569', fontSize: '1.08rem', lineHeight: 1.55 }}>
            Core MVP demo: upload purchase lots CSV, upload sales data CSV, run monthly COGS, and review SKU-level COGS results. This screen uses checked-in fixture artifacts only.
          </p>
        </section>

        <section id="process" style={{ marginBottom: '1rem' }}>
          <div style={grid}>
            <StepCard number="1" title="Upload purchase lots CSV" body={`Fixture selected: ${demoRun.inputs.purchaseLots}`} />
            <StepCard number="2" title="Upload sales data CSV" body={`Fixture selected: ${demoRun.inputs.movement}`} />
            <StepCard number="3" title="Run monthly COGS" body="Month selected: 2026-05. Run is simulated from local demo output generated by the FIFO engine." />
          </div>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ margin: '0 0 0.35rem' }}>SKU-level COGS results</h2>
              <p style={{ margin: 0, color: '#64748b' }}>
                Unit cost is merchandise cost per unit from the fixture lots. Shipping cost is the fixture freight cost allocated to units sold. Average cost is total cost divided by units sold.
              </p>
            </div>
            <DownloadCsvLink rows={rows} />
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {['SKU', 'Units Sold', 'Unit Cost', 'Shipping Cost', 'Total Cost', 'Average Cost'].map((header) => (
                    <th key={header} style={{ ...cellStyle, background: '#f9fafb', color: '#374151', fontWeight: 900 }}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.sku}>
                    <td style={cellStyle}>{row.sku}</td>
                    <td style={cellStyle}>{number(row.unitsSold)}</td>
                    <td style={cellStyle}>{money(row.unitCost)}</td>
                    <td style={cellStyle}>{money(row.shippingCost)}</td>
                    <td style={cellStyle}>{money(row.totalCost)}</td>
                    <td style={cellStyle}>{money(row.averageCost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Run totals</h2>
          <div style={grid}>
            <div><strong>Total COGS:</strong> {money(totalCogs)}</div>
            <div><strong>Units sold:</strong> {number(unitsSold)}</div>
            <div><strong>SKUs processed:</strong> {number(rows.length)}</div>
          </div>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Optional details</h2>
          <Shortfalls />
          <p style={{ margin: '1rem 0 0', color: '#64748b' }}>
            Safe check: <code>{demoRun.inputs.safeCheckCommand}</code> · Artifact directory: <code>{demoRun.inputs.artifactDirectory}</code>
          </p>
        </section>
      </div>
    </main>
  );
}
