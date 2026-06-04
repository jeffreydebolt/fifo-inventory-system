import React, { useState } from 'react';
import { demoRun } from '../demoData';
import {
  amazonConnectorMock,
  closeActionQueue,
  columnMappings,
  demandPlanning,
  exceptionGuidance,
  exportPacketChecklist,
  exportPacketManifest,
  intakeModes,
  inventoryTracking,
  replenishmentPlan,
  uploadMockFiles,
  valuationSnapshots
} from '../workflowMocks';

const page = {
  minHeight: '100vh',
  background: 'linear-gradient(180deg, #f8fafc 0%, #eef2ff 45%, #f8fafc 100%)',
  color: '#111827',
  padding: '2rem'
};

const shell = { maxWidth: '1180px', margin: '0 auto' };

const card = {
  background: 'rgba(255,255,255,0.96)',
  border: '1px solid #e5e7eb',
  borderRadius: '18px',
  boxShadow: '0 18px 45px rgba(15, 23, 42, 0.08)',
  overflow: 'hidden'
};

const softCard = {
  ...card,
  boxShadow: '0 8px 24px rgba(15, 23, 42, 0.06)'
};

const grid = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
  gap: '1rem'
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

function money(value) {
  return Number(value).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
}

function total(rows, key) {
  return rows.reduce((sum, row) => sum + Number(row[key] || 0), 0);
}

function titleize(key) {
  return key.replaceAll('_', ' ');
}

function Pill({ children, tone = 'blue' }) {
  const tones = {
    blue: ['#dbeafe', '#1d4ed8'],
    green: ['#dcfce7', '#166534'],
    amber: ['#fef3c7', '#92400e'],
    red: ['#fee2e2', '#991b1b'],
    slate: ['#e2e8f0', '#334155']
  };
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.35rem',
      background: tones[tone][0],
      color: tones[tone][1],
      fontWeight: 800,
      borderRadius: '999px',
      padding: '0.36rem 0.72rem',
      fontSize: '0.78rem',
      letterSpacing: '0.01em'
    }}>
      {children}
    </span>
  );
}

function StepCard({ number, title, body, status, tone = 'blue' }) {
  return (
    <div style={{ ...softCard, padding: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', marginBottom: '0.65rem' }}>
        <span style={{
          width: '2rem',
          height: '2rem',
          display: 'grid',
          placeItems: 'center',
          borderRadius: '0.75rem',
          background: '#111827',
          color: 'white',
          fontWeight: 900
        }}>{number}</span>
        <Pill tone={tone}>{status}</Pill>
      </div>
      <h3 style={{ margin: '0 0 0.4rem', fontSize: '1rem' }}>{title}</h3>
      <p style={{ margin: 0, color: '#4b5563', lineHeight: 1.45 }}>{body}</p>
    </div>
  );
}

function MetricCard({ label, value, note, tone = 'slate' }) {
  const accent = {
    slate: '#64748b',
    green: '#16a34a',
    amber: '#d97706',
    blue: '#2563eb',
    red: '#dc2626'
  }[tone];
  return (
    <div style={{ ...softCard, padding: '1.1rem', borderTop: `4px solid ${accent}` }}>
      <div style={{ color: '#64748b', fontSize: '0.82rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontSize: '1.75rem', fontWeight: 900, marginTop: '0.35rem' }}>{value}</div>
      <div style={{ color: '#64748b', marginTop: '0.35rem', lineHeight: 1.35 }}>{note}</div>
    </div>
  );
}

function DemoTable({ title, rows, emptyText }) {
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return (
    <section style={softCard}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e5e7eb', background: '#f9fafb' }}>
        <h3 style={{ margin: 0, fontSize: '1rem' }}>{title}</h3>
      </div>
      {rows.length === 0 ? (
        <p style={{ padding: '1rem', margin: 0 }}>{emptyText || 'No rows.'}</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} style={{ ...cellStyle, background: '#f9fafb', fontWeight: 800, color: '#374151', textTransform: 'capitalize' }}>
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

function DownloadLink({ sectionName, rows, label }) {
  const href = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(rows, null, 2))}`;
  return (
    <a
      href={href}
      download={`${sectionName}.json`}
      style={{
        color: '#1d4ed8',
        background: '#eff6ff',
        border: '1px solid #bfdbfe',
        fontWeight: 800,
        textDecoration: 'none',
        borderRadius: '0.85rem',
        padding: '0.8rem 0.9rem',
        display: 'block'
      }}
    >
      Export {label}
    </a>
  );
}

function MappingReview() {
  return (
    <section style={{ ...softCard, padding: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div>
          <h2 style={{ margin: '0 0 0.35rem' }}>Mapping review</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>Static MVP mock showing how uploaded columns will be confirmed before running FIFO.</p>
        </div>
        <Pill tone="green">All required demo columns present</Pill>
      </div>
      <div style={grid}>
        {columnMappings.map((mapping) => (
          <div key={mapping.source} style={{ border: '1px solid #e5e7eb', borderRadius: '0.9rem', padding: '0.9rem', background: '#f8fafc' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center' }}>
              <strong>{mapping.source}</strong>
              <Pill tone={mapping.tone}>{mapping.required ? 'Required' : 'Optional'}</Pill>
            </div>
            <p style={{ margin: '0.45rem 0', color: '#475569' }}>{mapping.matched.join(', ')}</p>
            <p style={{ margin: '0 0 0.65rem', color: '#64748b', lineHeight: 1.4 }}>{mapping.reviewNote}</p>
            <Pill tone={mapping.tone}>{mapping.status}</Pill>
          </div>
        ))}
      </div>
    </section>
  );
}

function IntakeModeReview({ mode, onModeChange }) {
  const active = intakeModes[mode];
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem', borderColor: mode === 'sample' ? '#bbf7d0' : '#fde68a' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone={active.tone}>{active.status}</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Intake mode: {active.label}</h2>
          <p style={{ margin: 0, color: '#4b5563', lineHeight: 1.5 }}>{active.body}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'start', flexWrap: 'wrap' }}>
          {Object.values(intakeModes).map((option) => (
            <button
              key={option.key}
              type="button"
              onClick={() => onModeChange(option.key)}
              style={{
                border: option.key === mode ? '2px solid #111827' : '1px solid #cbd5e1',
                background: option.key === mode ? '#111827' : 'white',
                color: option.key === mode ? 'white' : '#334155',
                borderRadius: '0.85rem',
                padding: '0.75rem 0.9rem',
                fontWeight: 900,
                cursor: 'pointer'
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '1rem', padding: '1rem' }}>
        <strong>{active.headline}</strong>
        <p style={{ margin: '0.45rem 0 0', color: '#475569' }}>Next action: {active.nextAction}</p>
      </div>
    </section>
  );
}

function UploadMockReview() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem', borderColor: '#fed7aa' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="amber">Upload mock queue</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Sample/upload review before mapping</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>Shows the future upload acceptance checklist while keeping file pickers and storage writes disabled.</p>
        </div>
        <Pill tone="green">No file leaves the browser</Pill>
      </div>
      <DemoTable title="Mock intake files" rows={uploadMockFiles} />
      <div style={{ marginTop: '1rem', border: '1px dashed #f59e0b', borderRadius: '1rem', padding: '1rem', background: '#fffbeb', color: '#92400e' }}>
        Real uploads remain quarantined until reviewed. Autonomous demo mode only previews filenames, row counts, required-column coverage, and next operator guidance.
      </div>
    </section>
  );
}

function ActionGuidance() {
  return (
    <div style={{ display: 'grid', gap: '0.85rem', marginTop: '1rem' }}>
      {exceptionGuidance.map((item) => (
        <div key={item.title} style={{ display: 'grid', gridTemplateColumns: 'minmax(130px, 0.35fr) 1fr', gap: '0.8rem', border: '1px solid #e5e7eb', borderRadius: '1rem', padding: '0.95rem', background: '#fff' }}>
          <div>
            <Pill tone={item.tone}>{item.severity}</Pill>
            <div style={{ color: '#64748b', marginTop: '0.5rem', fontWeight: 800 }}>{item.owner}</div>
          </div>
          <div>
            <strong>{item.title}</strong>
            <p style={{ margin: '0.4rem 0 0', color: '#475569', lineHeight: 1.45 }}>{item.action}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function InventoryTrackingMock() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="blue">Inventory tracking mock</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>On-hand, inbound, adjustments, and valuation snapshots</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>Fixture-only planning layer showing how FirstLot can move beyond month-end COGS into inventory control.</p>
        </div>
        <Pill tone="green">Local mock data only</Pill>
      </div>
      <div style={grid}>
        {inventoryTracking.map((item) => (
          <div key={item.sku} style={{ border: '1px solid #e5e7eb', borderRadius: '1rem', padding: '1rem', background: '#f8fafc' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
              <strong>{item.sku}</strong>
              <Pill tone={item.status === 'Healthy' ? 'green' : item.status === 'Watch' ? 'amber' : 'red'}>{item.status}</Pill>
            </div>
            <p style={{ margin: '0.65rem 0', color: '#475569' }}>On hand: <strong>{item.onHand}</strong> · Inbound: <strong>{item.inbound}</strong> · Adjustments: <strong>{item.adjustments}</strong></p>
            <p style={{ margin: '0 0 0.65rem', color: '#475569' }}>Valuation snapshot: <strong>{money(item.valuation)}</strong></p>
            <p style={{ margin: 0, color: '#64748b', lineHeight: 1.4 }}>{item.guidance}</p>
          </div>
        ))}
      </div>
      <div style={{ ...grid, marginTop: '1rem' }}>
        {valuationSnapshots.map(([label, value]) => (
          <div key={label} style={{ background: '#eef2ff', borderRadius: '0.9rem', padding: '0.9rem', border: '1px solid #c7d2fe' }}>
            <div style={{ color: '#4338ca', fontWeight: 900 }}>{label}</div>
            <div style={{ fontSize: '1.35rem', fontWeight: 900, marginTop: '0.25rem' }}>{value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function DemandPlanningMock() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="amber">Demand-planning mock</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Velocity, lead time, reorder guidance, and margin impact</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>Static local mock demonstrating the future planner without Amazon, Shopify, or production API calls.</p>
        </div>
        <Pill tone="slate">No connector execution</Pill>
      </div>
      <DemoTable title="Planner recommendations" rows={demandPlanning} />
      <div style={{ marginTop: '1rem' }}>
        <DemoTable title="Replenishment action plan" rows={replenishmentPlan} />
      </div>
    </section>
  );
}

function CloseActionQueue() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem', borderColor: '#bfdbfe' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="blue">Close action queue</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Operator guidance after the run</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>A concise safe next-step lane so FirstLot reads like an assistant, not a raw dashboard.</p>
        </div>
        <Pill tone="slate">Fixture decisions only</Pill>
      </div>
      <div style={grid}>
        {closeActionQueue.map((item) => (
          <div key={item.step} style={{ border: '1px solid #e5e7eb', borderRadius: '1rem', padding: '1rem', background: '#f8fafc' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem', marginBottom: '0.65rem' }}>
              <span style={{ width: '2rem', height: '2rem', borderRadius: '999px', display: 'grid', placeItems: 'center', background: '#111827', color: 'white', fontWeight: 900 }}>{item.step}</span>
              <Pill tone={item.tone}>{item.title}</Pill>
            </div>
            <p style={{ margin: 0, color: '#475569', lineHeight: 1.45 }}>{item.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ExportPacketChecklist() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="green">Export packet polish</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Close packet checklist</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>Shows what accounting receives, who reviews it, and why each artifact belongs in the close packet.</p>
        </div>
        <Pill tone="green">No-network downloads</Pill>
      </div>
      <DemoTable title="Close packet artifacts" rows={exportPacketChecklist} />
      <div style={{ marginTop: '1rem' }}>
        <DemoTable title="Export manifest and sign-off gates" rows={exportPacketManifest} />
      </div>
      <div style={{ marginTop: '1rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '1rem', padding: '1rem' }}>
        <strong>Draft close notes</strong>
        <p style={{ margin: '0.45rem 0 0', color: '#475569', lineHeight: 1.45 }}>
          May fixture run generated FIFO COGS, ending layers, one inventory exception, and an audit trail. Export after SKU-C exception is resolved or signed off.
        </p>
      </div>
    </section>
  );
}

function AmazonConnectorMock() {
  return (
    <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem', borderColor: '#fde68a' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <div>
          <Pill tone="amber">Local connector mock</Pill>
          <h2 style={{ margin: '0.75rem 0 0.35rem' }}>{amazonConnectorMock.headline}</h2>
          <p style={{ margin: 0, color: '#4b5563' }}>{amazonConnectorMock.safety}</p>
        </div>
        <Pill tone="red">Production APIs disabled</Pill>
      </div>
      <div style={grid}>
        {amazonConnectorMock.lanes.map((lane) => (
          <div key={lane.name} style={{ border: '1px solid #e5e7eb', borderRadius: '1rem', padding: '1rem', background: '#fff7ed' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center' }}>
              <strong>{lane.name}</strong>
              <Pill tone={lane.status === 'Mock contract' ? 'green' : 'amber'}>{lane.status}</Pill>
            </div>
            <p style={{ margin: '0.55rem 0', color: '#7c2d12' }}>Fixture: <strong>{lane.source}</strong> → {lane.mappedTo}</p>
            <p style={{ margin: 0, color: '#9a3412', lineHeight: 1.4 }}>{lane.guardrail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function DemoPage() {
  const [intakeMode, setIntakeMode] = useState('sample');
  const totalCogs = total(demoRun.cogsSummary, 'total_cogs');
  const inventoryValue = total(demoRun.remainingLayers, 'remaining_value');
  const lotsConsumed = new Set(demoRun.auditTrail.map((row) => row.lot_id)).size;
  const skuCount = new Set([...demoRun.cogsSummary.map((row) => row.sku), ...demoRun.shortfalls.map((row) => row.sku)]).size;

  return (
    <main style={page}>
      <div style={shell}>
        <section style={{ ...card, padding: '1.5rem', marginBottom: '1.25rem', borderColor: '#bfdbfe' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1.25rem', flexWrap: 'wrap' }}>
            <div style={{ maxWidth: '760px' }}>
              <Pill tone="green">{demoRun.safetyMode}</Pill>
              <h1 style={{ margin: '1rem 0 0.6rem', fontSize: 'clamp(2rem, 4vw, 3.5rem)', lineHeight: 1.02 }}>
                Close inventory with FIFO confidence.
              </h1>
              <p style={{ margin: 0, color: '#475569', fontSize: '1.1rem', lineHeight: 1.55 }}>
                FirstLot turns purchase lots and sales movement into FIFO COGS, remaining inventory layers, close exceptions, and a reviewable export packet for accounting.
              </p>
            </div>
            <div style={{ minWidth: '245px', ...softCard, padding: '1rem', background: '#f8fafc' }}>
              <strong>Friday MVP mode</strong>
              <p style={{ margin: '0.45rem 0 0', color: '#475569', lineHeight: 1.45 }}>
                Uses checked-in sample artifacts only. No live DB writes, no Storage Standard mutation, and no API fetches.
              </p>
            </div>
          </div>
          <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <a href="#setup" style={{ background: '#111827', color: 'white', padding: '0.85rem 1rem', borderRadius: '0.9rem', textDecoration: 'none', fontWeight: 900 }}>Start inventory close</a>
            <a href="/demo" style={{ background: '#dbeafe', color: '#1d4ed8', padding: '0.85rem 1rem', borderRadius: '0.9rem', textDecoration: 'none', fontWeight: 900 }}>Use sample data</a>
            <a href="/upload" style={{ background: '#fef3c7', color: '#92400e', padding: '0.85rem 1rem', borderRadius: '0.9rem', textDecoration: 'none', fontWeight: 900 }}>Upload mock / quarantined</a>
          </div>
        </section>

        <IntakeModeReview mode={intakeMode} onModeChange={setIntakeMode} />

        <UploadMockReview />

        <section id="setup" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: '1rem', marginBottom: '0.75rem', flexWrap: 'wrap' }}>
            <div>
              <h2 style={{ margin: 0 }}>Workflow preview</h2>
              <p style={{ margin: '0.35rem 0 0', color: '#64748b' }}>setup/start → sample data or upload/map mock → run/review exceptions → results summary → drilldowns → export packet</p>
            </div>
            <Pill tone="blue">Generated {demoRun.generatedAt}</Pill>
          </div>
          <div style={grid}>
            <StepCard number="1" title="Setup / start" status="Sample data selected" tone="green" body="Start the close from purchase lots and movement files, or use the checked-in sample packet for review." />
            <StepCard number="2" title="Data intake" status="Local fixture mode" tone="green" body={`Lots: ${demoRun.inputs.purchaseLots}. Movement: ${demoRun.inputs.movement}.`} />
            <StepCard number="3" title="Map columns" status="Static mock" tone="amber" body="Required columns are reviewed before the run; landed-cost and SKU mapping lanes are mocked for Friday MVP." />
            <StepCard number="4" title="Review exceptions" status={`${demoRun.shortfalls.length} needs attention`} tone="red" body="Exceptions are promoted ahead of raw tables so the operator knows what blocks a clean close." />
          </div>
        </section>

        <div style={{ marginBottom: '1.25rem' }}>
          <MappingReview />
        </div>

        <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem', borderColor: '#fecaca' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <div>
              <Pill tone="red">Exception-first review</Pill>
              <h2 style={{ margin: '0.75rem 0 0.35rem' }}>Here’s what needs attention before close.</h2>
              <p style={{ margin: 0, color: '#4b5563' }}>The demo run surfaces insufficient inventory before showing the successful COGS/layer drilldowns.</p>
            </div>
            <Pill tone={demoRun.shortfalls.length ? 'red' : 'green'}>{demoRun.shortfalls.length ? 'Close has exceptions' : 'Ready to close'}</Pill>
          </div>
          <div style={grid}>
            {demoRun.shortfalls.map((row) => (
              <div key={`${row.sale_id}-${row.sku}`} style={{ background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: '1rem', padding: '1rem' }}>
                <strong>{row.reason}</strong>
                <p style={{ margin: '0.5rem 0', color: '#7c2d12' }}>{row.message}</p>
                <div style={{ color: '#9a3412' }}>Sale {row.sale_id} · requested {row.requested_quantity} · allocated {row.allocated_quantity} · short {row.shortfall_quantity}</div>
              </div>
            ))}
          </div>
          <ActionGuidance />
        </section>

        <CloseActionQueue />

        <section style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ margin: '0 0 0.75rem' }}>Results summary</h2>
          <div style={grid}>
            <MetricCard label="Total FIFO COGS" value={money(totalCogs)} note="Calculated from local fixture lots consumed by May movement." tone="blue" />
            <MetricCard label="Inventory value remaining" value={money(inventoryValue)} note={`${demoRun.remainingLayers.length} remaining FIFO layer in the sample close.`} tone="green" />
            <MetricCard label="Shortfall count" value={demoRun.shortfalls.length} note="Promoted to the top of the close workflow." tone="red" />
            <MetricCard label="SKUs processed" value={skuCount} note={`${lotsConsumed} lots consumed across ${demoRun.auditTrail.length} audit rows.`} tone="slate" />
          </div>
        </section>

        <section style={{ ...softCard, padding: '1.25rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
            <div>
              <h2 style={{ margin: '0 0 0.35rem' }}>Export packet preview</h2>
              <p style={{ margin: 0, color: '#4b5563' }}>A local close packet accounting can review: summary, remaining layers, exceptions, and lot-level audit trail.</p>
            </div>
            <Pill tone="green">Data URI downloads only — no network</Pill>
          </div>
          <div style={grid}>
            <DownloadLink sectionName="cogs_summary" label="COGS summary JSON" rows={demoRun.cogsSummary} />
            <DownloadLink sectionName="remaining_layers" label="remaining layers JSON" rows={demoRun.remainingLayers} />
            <DownloadLink sectionName="shortfalls" label="exceptions JSON" rows={demoRun.shortfalls} />
            <DownloadLink sectionName="audit_trail" label="audit trail JSON" rows={demoRun.auditTrail} />
            <DownloadLink sectionName="export_manifest" label="export manifest JSON" rows={exportPacketManifest} />
          </div>
          <p style={{ margin: '1rem 0 0', color: '#64748b' }}>
            Regenerate: <code>{demoRun.inputs.regenerateCommand}</code> · Safe check: <code>{demoRun.inputs.safeCheckCommand}</code> · Artifacts: <code>{demoRun.inputs.artifactDirectory}</code>
          </p>
        </section>

        <ExportPacketChecklist />

        <InventoryTrackingMock />

        <DemandPlanningMock />

        <AmazonConnectorMock />

        <section style={{ marginBottom: '1.25rem' }}>
          <div style={{ marginBottom: '0.75rem' }}>
            <h2 style={{ margin: 0 }}>Drilldown tables</h2>
            <p style={{ margin: '0.35rem 0 0', color: '#64748b' }}>The technical run outputs are preserved here as secondary details, not the primary product experience.</p>
          </div>
          <div style={{ display: 'grid', gap: '1rem' }}>
            <DemoTable title="COGS by SKU" rows={demoRun.cogsSummary} />
            <DemoTable title="Remaining inventory layers" rows={demoRun.remainingLayers} />
            <DemoTable title="Shortfalls / exceptions" rows={demoRun.shortfalls} emptyText="No shortfalls." />
            <DemoTable title="Sale-to-lot audit trail" rows={demoRun.auditTrail} />
          </div>
        </section>
      </div>
    </main>
  );
}
