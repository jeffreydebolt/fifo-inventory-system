import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

global.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;
let originalFetch;

const overcomplicatedTerms = [
  'Mapping review',
  'Mapping confidence checklist',
  'planning assistant',
  'Inventory tracking mock',
  'Demand-planning mock',
  'Replenishment action plan',
  'Local connector mock',
  'Amazon connector mock',
  'Close action queue',
  'Close readiness timeline',
  'Export packet preview',
  'Export packet polish',
  'Accounting packet cover sheet',
  'Workflow preview',
  'Operator guidance after the run'
];

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
  originalFetch = global.fetch;
  global.fetch = jest.fn();
});

afterEach(() => {
  act(() => {
    root?.unmount();
  });
  root = null;
  container.remove();
  container = null;
  window.history.pushState({}, '', '/');
  global.fetch = originalFetch;
});

function renderAt(path) {
  window.history.pushState({}, '', path);
  act(() => {
    root = createRoot(container);
    root.render(<App />);
  });
}

function expectCoreMvpScreen() {
  expect(container.textContent).toContain('FirstLot FIFO COGS');
  expect(container.textContent).toContain('Local/demo mode');
  expect(container.textContent).toContain('Fixture/demo mode only — no live DB writes.');
  expect(container.textContent).toContain('fixture artifacts only');
  expect(container.textContent).toContain('Month close workflow');
  expect(container.textContent).toContain('Upload purchase lots CSV');
  expect(container.textContent).toContain('Upload sales CSV');
  expect(container.textContent).toContain('Run FIFO COGS for selected month');
  expect(container.textContent).toContain('Review SKU costs');
  expect(container.textContent).toContain('Fix failed SKUs and rerun');
  expect(container.textContent).toContain('Preserve close history');
  expect(container.textContent).toContain('Month selected: 2026-05');
  expect(container.textContent).toContain('SKU-level COGS results');
  expect(container.textContent).toContain('SKU');
  expect(container.textContent).toContain('Units sold');
  expect(container.textContent).toContain('Merchandise/unit cost');
  expect(container.textContent).toContain('Shipping cost');
  expect(container.textContent).toContain('Total COGS');
  expect(container.textContent).toContain('Average COGS');
  expect(container.textContent).toContain('Status');
  expect(container.textContent).toContain('SKU-A');
  expect(container.textContent).toContain('SKU-B');
  expect(container.textContent).toContain('$14.00');
  expect(container.textContent).toContain('$0.00');
  expect(container.textContent).toContain('$210.00');
  expect(container.textContent).toContain('$40.00');
  expect(container.textContent).toContain('Download results CSV');
  expect(container.textContent).toContain('Month history');
  expect(container.textContent).toContain('2026-04');
  expect(container.textContent).toContain('Run version');
  expect(container.textContent).toContain('Failed SKU queue');
  expect(container.textContent).toContain('SKU / month');
  expect(container.textContent).toContain('NEEDS FIX RERUN');
  expect(container.textContent).toContain('Sales quantity exceeds available FIFO lots.');
  expect(container.textContent).toContain('Upload corrected purchase lots CSV, validate, then rerun the full month.');
  expect(container.textContent).toContain('A failed SKU means sales exceeded available purchase lots for that SKU/month.');
  expect(container.textContent).toContain('Fix input CSV, rerun full month, then assert queue clear.');
  expect(container.textContent).toContain('Fix, rerun, append, and rollback audit');
  expect(container.textContent).toContain('Append/reopen version example');
  expect(container.textContent).toContain('Rollback audit / read-only');
  expect(container.textContent).toContain('does not execute rollback scripts');
  expect(container.textContent).toContain('Safe check: make check-firstlot-demo');

  for (const term of overcomplicatedTerms) {
    expect(container.textContent).not.toContain(term);
  }

  expect(global.fetch).not.toHaveBeenCalled();
}

test('renders /demo as Jeff core MVP process with checked-in local FIFO artifacts and no network calls', () => {
  renderAt('/demo');

  expectCoreMvpScreen();
});

test('renders / as the same safe fixture MVP process by default with no overcomplicated workflow sections', () => {
  renderAt('/');

  expectCoreMvpScreen();
});

test('labels /upload as quarantined legacy production upload and does not fetch', () => {
  renderAt('/upload');

  expect(container.textContent).toContain('Legacy production upload quarantined');
  expect(container.textContent).toContain('Upload and template actions are intentionally disabled');
  expect(container.textContent).toContain('Legacy Upload Disabled');
  expect(global.fetch).not.toHaveBeenCalled();
});
