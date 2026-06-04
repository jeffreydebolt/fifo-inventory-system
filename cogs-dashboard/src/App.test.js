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
  expect(container.textContent).toContain('fixture artifacts only');
  expect(container.textContent).toContain('Upload purchase lots CSV');
  expect(container.textContent).toContain('Upload sales data CSV');
  expect(container.textContent).toContain('Run monthly COGS');
  expect(container.textContent).toContain('Month selected: 2026-05');
  expect(container.textContent).toContain('SKU-level COGS results');
  expect(container.textContent).toContain('SKU');
  expect(container.textContent).toContain('Units Sold');
  expect(container.textContent).toContain('Unit Cost');
  expect(container.textContent).toContain('Shipping Cost');
  expect(container.textContent).toContain('Total Cost');
  expect(container.textContent).toContain('Average Cost');
  expect(container.textContent).toContain('SKU-A');
  expect(container.textContent).toContain('SKU-B');
  expect(container.textContent).toContain('$14.00');
  expect(container.textContent).toContain('$0.00');
  expect(container.textContent).toContain('$210.00');
  expect(container.textContent).toContain('$40.00');
  expect(container.textContent).toContain('Download results CSV');
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
