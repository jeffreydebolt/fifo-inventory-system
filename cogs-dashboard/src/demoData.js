import cogsSummary from './demo-output/firstlot_demo/cogs_summary.json';
import remainingLayers from './demo-output/firstlot_demo/remaining_layers.json';
import auditTrail from './demo-output/firstlot_demo/audit_trail.json';
import shortfalls from './demo-output/firstlot_demo/shortfalls.json';
import failedSkuQueue from './demo-output/firstlot_demo/failed_sku_queue.json';
import cogsDetail from './demo-output/firstlot_demo/cogs_detail.json';

export const demoRun = {
  generatedAt: '2026-06-03T23:00:00',
  safetyMode: 'Local/demo mode — fixture data only, no live DB writes',
  month: '2026-05',
  runVersion: 'v1',
  inputs: {
    purchaseLots: 'tests/fixtures/firstlot_demo/purchase_lots.csv',
    movement: 'tests/fixtures/firstlot_demo/movement.csv',
    artifactDirectory: 'cogs-dashboard/src/demo-output/firstlot_demo',
    regenerateCommand: 'python3 scripts/regenerate_firstlot_demo_artifacts.py',
    safeCheckCommand: 'make check-firstlot-demo'
  },
  cogsSummary,
  remainingLayers,
  auditTrail,
  shortfalls,
  failedSkuQueue,
  cogsDetail
};

export const monthHistory = [
  {
    month: '2026-05',
    status: 'Needs fix',
    runVersion: 'v1',
    cogsTotal: 250,
    failedSkus: 1,
    lastRun: 'Jun 3, 11:00 PM',
    note: 'Fixture run has one shortfall queued for fix/rerun.'
  },
  {
    month: '2026-04',
    status: 'Complete',
    runVersion: 'v2',
    cogsTotal: 1840,
    failedSkus: 0,
    lastRun: 'May 7, 4:10 PM',
    note: 'Prior fixture month completed after corrected lots append.'
  },
  {
    month: '2026-03',
    status: 'Reopened',
    runVersion: 'v1',
    cogsTotal: null,
    failedSkus: null,
    lastRun: 'Apr 2, 8:14 PM',
    note: 'Read-only rollback/reopen example; no rollback action is wired.'
  }
];

export const runVersions = [
  {
    month: '2026-04',
    version: 'v1',
    status: 'Needs fix',
    summary: 'Original run had missing purchase lots for 3 fixture SKUs.',
    delta: 'Baseline'
  },
  {
    month: '2026-04',
    version: 'v2',
    status: 'Complete',
    summary: 'Corrected lots CSV appended, then full month rerun completed.',
    delta: '+$214.00 COGS across corrected fixture SKUs'
  }
];
