import cogsSummary from './demo-output/firstlot_demo/cogs_summary.json';
import remainingLayers from './demo-output/firstlot_demo/remaining_layers.json';
import auditTrail from './demo-output/firstlot_demo/audit_trail.json';
import shortfalls from './demo-output/firstlot_demo/shortfalls.json';

export const demoRun = {
  generatedAt: '2026-06-03T23:00:00',
  safetyMode: 'Local/demo mode — fixture data only, no live DB writes',
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
  shortfalls
};
