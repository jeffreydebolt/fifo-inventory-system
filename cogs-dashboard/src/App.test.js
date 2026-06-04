import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

global.IS_REACT_ACT_ENVIRONMENT = true;

let container;
let root;

beforeEach(() => {
  container = document.createElement('div');
  document.body.appendChild(container);
});

afterEach(() => {
  act(() => {
    root?.unmount();
  });
  root = null;
  container.remove();
  container = null;
  window.history.pushState({}, '', '/');
});

test('renders /demo with checked-in local FIFO artifacts and no network calls', () => {
  const originalFetch = global.fetch;
  global.fetch = jest.fn();
  window.history.pushState({}, '', '/demo');

  act(() => {
    root = createRoot(container);
    root.render(<App />);
  });

  expect(container.textContent).toContain('FirstLot local MVP demo');
  expect(container.textContent).toContain('Local/demo mode');
  expect(container.textContent).toContain('cogs-dashboard/src/demo-output/firstlot_demo');
  expect(container.textContent).toContain('SKU-A');
  expect(container.textContent).toContain('LOT-B-001');
  expect(container.textContent).toContain('INSUFFICIENT_INVENTORY');
  expect(global.fetch).not.toHaveBeenCalled();

  global.fetch = originalFetch;
});
