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

function expectCoreMvpScreen() {
  expect(container.textContent).toContain('FirstLot Inventory Command Center');
  expect(container.textContent).toContain('Local/demo mode');
  expect(container.textContent).toContain('no Seller Central/SP-API calls');
  expect(container.textContent).toContain('Fixture/demo mode only — no live DB writes.');
  expect(container.textContent).toContain('fixture artifacts only');
  expect(container.textContent).toContain('Operator story controls');
  expect(container.textContent).toContain('Display only · no mutations');
  expect(container.textContent).toContain('They are not wired to uploads, APIs, or data mutations in demo mode.');
  expect(container.textContent).toContain('Run monthly COGS');
  expect(container.textContent).toContain('Mock Amazon onboarding timeline');
  expect(container.textContent).toContain('Connect Amazon');
  expect(container.textContent).toContain('Pull SKUs and available inventory');
  expect(container.textContent).toContain('Confirm other warehouses');
  expect(container.textContent).toContain('Upload outside-Amazon SKU/counts');
  expect(container.textContent).toContain('Upload source-backed purchase lots/freight');
  expect(container.textContent).toContain('Match current in-stock to lots');
  expect(container.textContent).toContain('Propose FIFO day 0');
  expect(container.textContent).toContain('Connector approval boundary');
  expect(container.textContent).toContain('Live connector not approved');
  expect(container.textContent).toContain('Amazon OAuth');
  expect(container.textContent).toContain('credential loading');
  expect(container.textContent).toContain('Readiness gate');
  expect(container.textContent).toContain('Amazon sales history covers rollback window');
  expect(container.textContent).toContain('Estimated day-0 units');
  expect(container.textContent).toContain('Source support');
  expect(container.textContent).toContain('70.65%');
  expect(container.textContent).toContain('Day-0 rule basis');
  expect(container.textContent).toContain('Use the requested close month start as the first draft day 0.');
  expect(container.textContent).toContain('Source queue');
  expect(container.textContent).toContain('Supplier invoice + freight allocation');
  expect(container.textContent).toContain('SKU map decision');
  expect(container.textContent).toContain('receipts exceed current + sales');
  expect(container.textContent).toContain('Inventory tracking');
  expect(container.textContent).toContain('Amazon available');
  expect(container.textContent).toContain('Other warehouse available');
  expect(container.textContent).toContain('Total available');
  expect(container.textContent).toContain('Inbound');
  expect(container.textContent).toContain('Valuation');
  expect(container.textContent).toContain('Status/action');
  expect(container.textContent).toContain('Planning and replenishment');
  expect(container.textContent).toContain('Velocity');
  expect(container.textContent).toContain('Lead time');
  expect(container.textContent).toContain('Cover days');
  expect(container.textContent).toContain('Stockout risk');
  expect(container.textContent).toContain('Recommendation');
  expect(container.textContent).toContain('CAMERA-KIT');
  expect(container.textContent).toContain('Reorder now');
  expect(container.textContent).toContain('Local client-test file selection');
  expect(container.textContent).toContain('Choose local fixture packet');
  expect(container.textContent).toContain('No network calls · no uploads · fixture choices only');
  expect(container.textContent).toContain('Selected files');
  expect(container.textContent).toContain('Purchase lots CSV');
  expect(container.textContent).toContain('Sales CSV');
  expect(container.textContent).toContain('Run preview');
  expect(container.textContent).toContain('Selected month');
  expect(container.textContent).toContain('Validation status');
  expect(container.textContent).toContain('Generated artifacts');
  expect(container.textContent).toContain('Close packet');
  expect(container.textContent).toContain('Client-test controls are intentionally local page state only');
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
  expect(container.textContent).toContain('Fixed rerun artifacts');
  expect(container.textContent).toContain('Run v1: needs fix');
  expect(container.textContent).toContain('Run v2: complete after corrected purchase lots');
  expect(container.textContent).toContain('purchase_lots_fixed.csv');
  expect(container.textContent).toContain('failed SKU rows from 1 to 0');
  expect(container.textContent).toContain('firstlot_demo_fixed');
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

  expect(global.fetch).not.toHaveBeenCalled();
}

test('renders /demo as Jeff core MVP process with checked-in local FIFO artifacts and no network calls', () => {
  renderAt('/demo');

  expectCoreMvpScreen();
});

test('fixture selector changes the local client-test preview without network calls', () => {
  renderAt('/demo');

  const selector = container.querySelector('#client-fixture-select');
  expect(selector).not.toBeNull();

  act(() => {
    selector.value = 'second-synthetic-client';
    selector.dispatchEvent(new Event('change', { bubbles: true }));
  });

  expect(container.textContent).toContain('Second synthetic fixture client');
  expect(container.textContent).toContain('tests/fixtures/firstlot_second_synthetic_client/purchase_lots.csv');
  expect(container.textContent).toContain('Expected clear queue when run with --expect-clear');
  expect(global.fetch).not.toHaveBeenCalled();
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
