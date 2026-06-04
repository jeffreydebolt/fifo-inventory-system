import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

global.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;
let originalFetch;

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

test('renders /demo as a workflow product preview with checked-in local FIFO artifacts and no network calls', () => {
  renderAt('/demo');

  expect(container.textContent).toContain('Close inventory with FIFO confidence');
  expect(container.textContent).toContain('Local/demo mode');
  expect(container.textContent).toContain('setup/start → sample data or upload/map mock → run/review exceptions → results summary → drilldowns → export packet');
  expect(container.textContent).toContain('Mapping review');
  expect(container.textContent).toContain('Mapping confidence checklist');
  expect(container.textContent).toContain('Required FIFO keys');
  expect(container.textContent).toContain('Channel SKU aliases');
  expect(container.textContent).toContain('Upload mock queue');
  expect(container.textContent).toContain('Sample/upload review before mapping');
  expect(container.textContent).toContain('purchase_lots_sample.csv');
  expect(container.textContent).toContain('No file leaves the browser');
  expect(container.textContent).toContain('Needs operator review');
  expect(container.textContent).toContain('Exception-first review');
  expect(container.textContent).toContain('Resolve insufficient inventory before close');
  expect(container.textContent).toContain('Close action queue');
  expect(container.textContent).toContain('Operator guidance after the run');
  expect(container.textContent).toContain('Close readiness timeline');
  expect(container.textContent).toContain('What can close now, and what still needs sign-off?');
  expect(container.textContent).toContain('Exception blocks final approval');
  expect(container.textContent).toContain('Accounting packet');
  expect(container.textContent).toContain('Export packet polish');
  expect(container.textContent).toContain('Close packet checklist');
  expect(container.textContent).toContain('Accounting packet cover sheet');
  expect(container.textContent).toContain('May inventory close review');
  expect(container.textContent).toContain('Export manifest and sign-off gates');
  expect(container.textContent).toContain('Blocked until reviewed');
  expect(container.textContent).toContain('export manifest JSON');
  expect(container.textContent).toContain('Close notes');
  expect(container.textContent).toContain('Inventory tracking mock');
  expect(container.textContent).toContain('On-hand, inbound, adjustments, and valuation snapshots');
  expect(container.textContent).toContain('Demand-planning mock');
  expect(container.textContent).toContain('Velocity, lead time, reorder guidance, and margin impact');
  expect(container.textContent).toContain('Replenishment action plan');
  expect(container.textContent).toContain('Escalate replenishment');
  expect(container.textContent).toContain('Local connector mock');
  expect(container.textContent).toContain('Amazon connector mock: import-only, local fixture contract');
  expect(container.textContent).toContain('No Seller Central, SP-API, settlement, or order endpoint is called');
  expect(container.textContent).toContain('amazon_orders_fixture.csv');
  expect(container.textContent).toContain('Results summary');
  expect(container.textContent).toContain('Export packet preview');
  expect(container.textContent).toContain('Drilldown tables');
  expect(container.textContent).toContain('cogs-dashboard/src/demo-output/firstlot_demo');
  expect(container.textContent).toContain('python3 scripts/regenerate_firstlot_demo_artifacts.py');
  expect(container.textContent).toContain('make check-firstlot-demo');
  expect(container.textContent).toContain('SKU-A');
  expect(container.textContent).toContain('LOT-B-001');
  expect(container.textContent).toContain('INSUFFICIENT_INVENTORY');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('toggles between sample-data and upload-mock intake states without network calls', () => {
  renderAt('/demo');

  expect(container.textContent).toContain('Sample FIFO packet is ready to run');
  const uploadMockButton = Array.from(container.querySelectorAll('button')).find((button) => button.textContent === 'Upload mock');

  act(() => {
    uploadMockButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });

  expect(container.textContent).toContain('Upload lane is mocked and does not send files');
  expect(container.textContent).toContain('File pickers, production APIs, and live storage writes stay disabled');
  expect(container.textContent).toContain('Review mappings before enabling real uploads');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('renders / as the safe fixture workflow by default with no network calls', () => {
  renderAt('/');

  expect(container.textContent).toContain('Friday MVP mode');
  expect(container.textContent).toContain('Uses checked-in sample artifacts only');
  expect(container.textContent).toContain('No live DB writes');
  expect(container.textContent).toContain('no API fetches');
  expect(container.textContent).toContain('Start inventory close');
  expect(global.fetch).not.toHaveBeenCalled();
});

test('labels /upload as quarantined legacy production upload and does not fetch', () => {
  renderAt('/upload');

  expect(container.textContent).toContain('Legacy production upload quarantined');
  expect(container.textContent).toContain('Upload and template actions are intentionally disabled');
  expect(container.textContent).toContain('Legacy Upload Disabled');
  expect(global.fetch).not.toHaveBeenCalled();
});
