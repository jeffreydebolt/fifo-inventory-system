import React from 'react';
import { demoRun, monthHistory, runVersions } from '../demoData';

const page = {
  minHeight: '100vh',
  background: '#f8fafc',
  color: '#111827',
  padding: '2rem'
};

const shell = { maxWidth: '1120px', margin: '0 auto' };

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
  textAlign: 'left',
  verticalAlign: 'top'
};

function money(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  return Number(value).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function number(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  return Number(value).toLocaleString('en-US');
}

function cogsRows() {
  return demoRun.cogsDetail.map((row) => ({
    sku: row.sku,
    unitsSold: Number(row.total_quantity_sold),
    unitCost: Number(row.merchandise_cost) / Number(row.total_quantity_sold),
    shippingCost: Number(row.shipping_cost),
    totalCost: Number(row.total_cost),
    averageCost: Number(row.average_cost),
    status: demoRun.shortfalls.some((shortfall) => shortfall.sku === row.sku) ? 'Needs fix' : 'Complete'
  }));
}

function Pill({ children, tone = 'green' }) {
  const tones = {
    green: { background: '#dcfce7', color: '#166534' },
    amber: { background: '#fef3c7', color: '#92400e' },
    slate: { background: '#e2e8f0', color: '#334155' }
  };

  return (
    <span style={{
      display: 'inline-flex',
      ...tones[tone],
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
    ['SKU', 'Units sold', 'Merchandise/unit cost', 'Shipping cost', 'Total COGS', 'Average COGS', 'Status'].join(','),
    ...rows.map((row) => [
      row.sku,
      row.unitsSold,
      row.unitCost.toFixed(2),
      row.shippingCost.toFixed(2),
      row.totalCost.toFixed(2),
      row.averageCost.toFixed(2),
      row.status
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

function issueLabel(row) {
  if (row.reason === 'INSUFFICIENT_INVENTORY') {
    return 'Sales quantity exceeds available FIFO lots.';
  }

  return 'No purchase lot found for this SKU before sale date.';
}

function FailedSkuQueue() {
  if (demoRun.failedSkuQueue.length === 0) {
    return <p style={{ margin: 0, color: '#166534' }}>No failed SKUs in this fixture run.</p>;
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['SKU / month', 'Issue', 'Requested / allocated / short', 'Suggested fix', 'Fix/rerun status'].map((header) => (
              <th key={header} style={{ ...cellStyle, background: '#fff7ed', color: '#9a3412', fontWeight: 900 }}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {demoRun.failedSkuQueue.map((queueRow) => {
            const saleIssues = demoRun.shortfalls.filter((shortfall) => (
              shortfall.sku === queueRow.sku && shortfall.sale_date.startsWith(queueRow.period)
            ));
            return (
              <tr key={`${queueRow.period}-${queueRow.sku}`}>
                <td style={cellStyle}>
                  <strong>{queueRow.sku}</strong><br />
                  {queueRow.period} · {number(queueRow.failure_count)} sale issue(s)
                </td>
                <td style={cellStyle}>
                  {saleIssues.map((issue) => (
                    <div key={issue.sale_id}>{issue.sale_id}: {issueLabel(issue)}</div>
                  ))}
                </td>
                <td style={cellStyle}>
                  {number(queueRow.requested_quantity)} requested; {number(queueRow.allocated_quantity)} allocated; short {number(queueRow.shortfall_quantity)}
                </td>
                <td style={cellStyle}>Upload corrected purchase lots CSV, validate, then rerun the full month.</td>
                <td style={cellStyle}><Pill tone="amber">{queueRow.status.replaceAll('_', ' ')}</Pill></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function MonthHistory() {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {['Month', 'Status', 'Run version', 'COGS total', 'Failed SKUs', 'Last run', 'Operator note'].map((header) => (
              <th key={header} style={{ ...cellStyle, background: '#f9fafb', color: '#374151', fontWeight: 900 }}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {monthHistory.map((row) => (
            <tr key={row.month}>
              <td style={cellStyle}><strong>{row.month}</strong></td>
              <td style={cellStyle}><Pill tone={row.status === 'Complete' ? 'green' : 'amber'}>{row.status}</Pill></td>
              <td style={cellStyle}>{row.runVersion}</td>
              <td style={cellStyle}>{money(row.cogsTotal)}</td>
              <td style={cellStyle}>{number(row.failedSkus)}</td>
              <td style={cellStyle}>{row.lastRun}</td>
              <td style={cellStyle}>{row.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RerunAndRollbackAudit() {
  return (
    <div style={grid}>
      <div style={{ ...card, padding: '1rem', boxShadow: 'none' }}>
        <h3 style={{ margin: '0 0 0.6rem' }}>Fix/rerun flow</h3>
        <ol style={{ margin: 0, paddingLeft: '1.25rem', color: '#475569', lineHeight: 1.6 }}>
          <li>Review failed SKU queue.</li>
          <li>Upload corrected purchase lots CSV or corrected sales CSV.</li>
          <li>Run local validation.</li>
          <li>Rerun the full month and compare COGS before finalizing.</li>
        </ol>
        <p style={{ margin: '0.8rem 0 0', color: '#92400e', fontWeight: 800 }}>Buttons are intentionally not wired in this fixture-only UI.</p>
      </div>

      <div style={{ ...card, padding: '1rem', boxShadow: 'none' }}>
        <h3 style={{ margin: '0 0 0.6rem' }}>Append/reopen version example</h3>
        {runVersions.map((version) => (
          <div key={`${version.month}-${version.version}`} style={{ borderTop: '1px solid #e5e7eb', paddingTop: '0.7rem', marginTop: '0.7rem' }}>
            <strong>{version.month} run {version.version} — {version.status}</strong>
            <p style={{ margin: '0.25rem 0', color: '#475569' }}>{version.summary}</p>
            <p style={{ margin: 0, color: '#334155' }}>Delta: {version.delta}</p>
          </div>
        ))}
      </div>

      <div style={{ ...card, padding: '1rem', boxShadow: 'none' }}>
        <h3 style={{ margin: '0 0 0.6rem' }}>Rollback audit / read-only</h3>
        <p style={{ margin: 0, color: '#475569', lineHeight: 1.55 }}>
          Rollback and reopen are shown as audit states only. This demo does not execute rollback scripts, does not write a database, and preserves prior run versions as read-only history.
        </p>
        <p style={{ margin: '0.8rem 0 0', color: '#334155' }}><strong>Audit source:</strong> checked-in fixture audit trail rows: {number(demoRun.auditTrail.length)}</p>
      </div>
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
            Core MVP demo: upload purchase lots CSV, upload sales data CSV, run monthly COGS, and review SKU-level unit, shipping, total, and average COGS. This screen uses checked-in fixture artifacts only.
          </p>
        </section>

        <section style={{ ...card, padding: '1rem 1.25rem', marginBottom: '1rem', borderColor: '#fed7aa', background: '#fff7ed' }}>
          <h2 style={{ margin: '0 0 0.35rem', color: '#9a3412' }}>Fixture/demo mode only — no live DB writes.</h2>
          <p style={{ margin: 0, color: '#7c2d12', lineHeight: 1.5 }}>
            This page is a local operator story backed by fixture CSVs and checked-in generated artifacts. Upload, run, fix, and rerun controls are descriptive only; nothing writes to Supabase, Storage Standard data, production APIs, or live inventory.
          </p>
        </section>

        <section id="process" style={{ marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Month close workflow</h2>
          <div style={grid}>
            <StepCard number="1" title="Upload purchase lots CSV" body={`Fixture selected: ${demoRun.inputs.purchaseLots}`} />
            <StepCard number="2" title="Upload sales CSV" body={`Fixture selected: ${demoRun.inputs.movement}`} />
            <StepCard number="3" title="Run FIFO COGS for selected month" body={`Month selected: ${demoRun.month}. Run ${demoRun.runVersion} is simulated from local FIFO engine output.`} />
            <StepCard number="4" title="Review SKU costs" body="Inspect units sold, merchandise/unit cost, shipping cost, total COGS, average COGS, and status for every fixture SKU." />
            <StepCard number="5" title="Fix failed SKUs and rerun" body="Failed SKUs require corrected local CSV inputs, then a full-month rerun with the queue asserted clear." />
            <StepCard number="6" title="Preserve close history" body="Each month/run status remains visible so reopened or appended fixture runs do not erase prior history." />
          </div>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ margin: '0 0 0.35rem' }}>SKU-level COGS results</h2>
              <p style={{ margin: 0, color: '#64748b' }}>
                Unit cost is merchandise cost per unit from fixture lots. Shipping cost is fixture freight allocated to units sold. Average cost is total cost divided by units sold.
              </p>
            </div>
            <DownloadCsvLink rows={rows} />
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  {['SKU', 'Units sold', 'Merchandise/unit cost', 'Shipping cost', 'Total COGS', 'Average COGS', 'Status'].map((header) => (
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
                    <td style={cellStyle}><Pill tone={row.status === 'Complete' ? 'green' : 'amber'}>{row.status}</Pill></td>
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
            <div><strong>Failed SKUs:</strong> {number(demoRun.failedSkuQueue.length)}</div>
          </div>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Month history</h2>
          <MonthHistory />
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Failed SKU queue</h2>
          <FailedSkuQueue />
          <p style={{ margin: '0.85rem 0 0', color: '#64748b', lineHeight: 1.5 }}>
            A failed SKU means sales exceeded available purchase lots for that SKU/month. Fix input CSV, rerun full month, then assert queue clear.
          </p>
        </section>

        <section style={{ ...card, padding: '1.25rem', marginBottom: '1rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Fix, rerun, append, and rollback audit</h2>
          <RerunAndRollbackAudit />
          <p style={{ margin: '1rem 0 0', color: '#64748b' }}>
            Safe check: <code>{demoRun.inputs.safeCheckCommand}</code> · Artifact directory: <code>{demoRun.inputs.artifactDirectory}</code>
          </p>
        </section>
      </div>
    </main>
  );
}
