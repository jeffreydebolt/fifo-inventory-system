import cogsSummary from './demo-output/firstlot_demo/cogs_summary.json';
import remainingLayers from './demo-output/firstlot_demo/remaining_layers.json';
import auditTrail from './demo-output/firstlot_demo/audit_trail.json';
import shortfalls from './demo-output/firstlot_demo/shortfalls.json';
import failedSkuQueue from './demo-output/firstlot_demo/failed_sku_queue.json';
import cogsDetail from './demo-output/firstlot_demo/cogs_detail.json';
import fixedCogsSummary from './demo-output/firstlot_demo_fixed/cogs_summary.json';
import fixedRemainingLayers from './demo-output/firstlot_demo_fixed/remaining_layers.json';
import fixedAuditTrail from './demo-output/firstlot_demo_fixed/audit_trail.json';
import fixedShortfalls from './demo-output/firstlot_demo_fixed/shortfalls.json';
import fixedFailedSkuQueue from './demo-output/firstlot_demo_fixed/failed_sku_queue.json';
import fixedCogsDetail from './demo-output/firstlot_demo_fixed/cogs_detail.json';
import fixedMonthHistory from './demo-output/firstlot_demo_fixed/month_history.json';

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

export const fixedDemoRun = {
  generatedAt: '2026-06-03T23:00:00',
  safetyMode: 'Local/demo mode — fixture data only, no live DB writes',
  month: '2026-05',
  runVersion: 'v2',
  inputs: {
    purchaseLots: 'tests/fixtures/firstlot_demo/purchase_lots_fixed.csv',
    movement: 'tests/fixtures/firstlot_demo/movement.csv',
    artifactDirectory: 'cogs-dashboard/src/demo-output/firstlot_demo_fixed',
    regenerateCommand: 'python3 scripts/regenerate_firstlot_demo_artifacts.py',
    assertClearCommand: 'python3 -m app.local_cli failed-skus --out cogs-dashboard/src/demo-output/firstlot_demo_fixed --period 2026-05 --assert-clear',
    compareCommand: 'python3 -m app.local_cli compare-runs --before cogs-dashboard/src/demo-output/firstlot_demo --after cogs-dashboard/src/demo-output/firstlot_demo_fixed --period 2026-05'
  },
  cogsSummary: fixedCogsSummary,
  remainingLayers: fixedRemainingLayers,
  auditTrail: fixedAuditTrail,
  shortfalls: fixedShortfalls,
  failedSkuQueue: fixedFailedSkuQueue,
  cogsDetail: fixedCogsDetail,
  monthHistory: fixedMonthHistory
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
    month: '2026-05',
    version: 'v1',
    status: 'Needs fix',
    summary: 'Original fixture run uses purchase_lots.csv and leaves SKU-A short by 1 unit.',
    delta: 'Baseline: $250.00 COGS, 1 failed SKU queued'
  },
  {
    month: '2026-05',
    version: 'v2',
    status: 'Complete',
    summary: 'Corrected purchase_lots_fixed.csv is rerun for the full month and clears the failed SKU queue.',
    delta: '+$13.00 COGS; SKU-A completed with 19 units sold and no shortfalls'
  }
];

export const clientTestFixtures = [
  {
    id: 'firstlot-demo-v1',
    label: 'FirstLot demo — v1 needs fix',
    client: 'Synthetic local demo client',
    period: '2026-05',
    purchaseLots: demoRun.inputs.purchaseLots,
    movement: demoRun.inputs.movement,
    artifactDirectory: demoRun.inputs.artifactDirectory,
    validationStatus: 'Valid fixture CSVs',
    runStatus: 'Needs fix rerun',
    queueSummary: '1 failed SKU queued (SKU-A short by 1 unit)',
    closePacket: 'cogs-dashboard/src/demo-output/firstlot_demo/close_packet.json'
  },
  {
    id: 'firstlot-demo-v2-fixed',
    label: 'FirstLot demo — v2 corrected rerun',
    client: 'Synthetic local demo client',
    period: '2026-05',
    purchaseLots: fixedDemoRun.inputs.purchaseLots,
    movement: fixedDemoRun.inputs.movement,
    artifactDirectory: fixedDemoRun.inputs.artifactDirectory,
    validationStatus: 'Valid fixture CSVs',
    runStatus: 'Complete after corrected purchase lots',
    queueSummary: '0 failed SKUs; assert-clear passes',
    closePacket: 'cogs-dashboard/src/demo-output/firstlot_demo_fixed/close_packet.json'
  },
  {
    id: 'second-synthetic-client',
    label: 'Second synthetic client — clean close',
    client: 'Second synthetic fixture client',
    period: '2026-06',
    purchaseLots: 'tests/fixtures/firstlot_second_synthetic_client/purchase_lots.csv',
    movement: 'tests/fixtures/firstlot_second_synthetic_client/movement.csv',
    artifactDirectory: '/tmp/firstlot-second-synthetic-client-check',
    validationStatus: 'Valid fixture CSVs via scripts/run_firstlot_client_fixture.py',
    runStatus: 'Client-test wrapper ready',
    queueSummary: 'Expected clear queue when run with --expect-clear',
    closePacket: '/tmp/firstlot-second-synthetic-client-check/close_packet.json'
  }
];

export const amazonOnboardingTimeline = [
  'Connect Amazon',
  'Pull SKUs and available inventory',
  'Confirm other warehouses',
  'Upload outside-Amazon SKU/counts',
  'Upload source-backed purchase lots/freight',
  'Match current in-stock to lots',
  'Propose FIFO day 0'
];

export const inventoryTrackingRows = [
  {
    sku: 'CAMERA-KIT',
    amazonAvailable: 42,
    amazonReserved: 3,
    otherWarehouseAvailable: 11,
    countStatus: 'Operator attested',
    totalAvailable: 53,
    sourceBackedUnits: 47,
    sourceGap: 6,
    inbound: 18,
    valuation: 669.75,
    statusAction: 'Blocked: upload freight bill + 6 more source-backed units'
  },
  {
    sku: 'TRIPOD',
    amazonAvailable: 16,
    amazonReserved: 1,
    otherWarehouseAvailable: 2,
    countStatus: 'Needs supervisor sign-off',
    totalAvailable: 18,
    sourceBackedUnits: 18,
    sourceGap: 0,
    inbound: 0,
    valuation: 466.20,
    statusAction: 'Blocked: approve QA hold count before day 0'
  },
  {
    sku: 'STRAP-BUNDLE',
    amazonAvailable: 7,
    amazonReserved: 0,
    otherWarehouseAvailable: 0,
    countStatus: 'Operator attested',
    totalAvailable: 7,
    sourceBackedUnits: 0,
    sourceGap: 7,
    inbound: 24,
    valuation: 0,
    statusAction: 'Blocked: upload invoice and freight allocation for inbound lot'
  }
];

export const dayZeroProposal = {
  proposedStartDate: '2026-05-01',
  confidence: 'Blocked · review required',
  currentUnitsToReconcile: 92,
  sourceBackedUnits: 65,
  ruleDraft: 'Earliest close month start where current Amazon + outside-warehouse stock can be backed to purchase lots/freight, with every exception carried as a blocker.',
  nextOperatorAction: 'Resolve blockers, upload/approve source-backed purchase lots and freight, then confirm or adjust FIFO day 0.'
};

export const dayZeroBlockers = [
  { sku: 'CAMERA-KIT', issue: 'Need source-backed lots for 6 more units and complete partial freight allocation.', action: 'Attach supplier invoice + freight bill before accepting day 0.' },
  { sku: 'TRIPOD', issue: 'Other-warehouse count is a QA hold pending supervisor sign-off.', action: 'Approve or exclude the 2 held units.' },
  { sku: 'STRAP-BUNDLE', issue: 'No draft source units matched and freight allocation is missing.', action: 'Upload inbound supplier invoice and freight allocation.' },
  { sku: 'LENS-CAP-ONLY', issue: 'Warehouse-only SKU is not mapped to Amazon catalog / FirstLot SKU map.', action: 'Map, archive, or exclude before day 0.' }
];

export const planningRows = [
  {
    sku: 'CAMERA-KIT',
    velocity: '5.8 units/day',
    leadTime: '21 days',
    coverDays: 9,
    stockoutRisk: 'High',
    recommendation: 'Reorder now; inbound does not fully cover lead time.'
  },
  {
    sku: 'TRIPOD',
    velocity: '1.2 units/day',
    leadTime: '14 days',
    coverDays: 15,
    stockoutRisk: 'Medium',
    recommendation: 'Confirm non-Amazon count before purchasing.'
  },
  {
    sku: 'STRAP-BUNDLE',
    velocity: '2.7 units/day',
    leadTime: '30 days',
    coverDays: 3,
    stockoutRisk: 'Critical',
    recommendation: 'Prioritize inbound receipt and source docs.'
  }
];
