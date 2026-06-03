export const demoRun = {
  generatedAt: '2026-06-03T23:00:00',
  safetyMode: 'Local/demo mode — fixture data only, no live DB writes',
  inputs: {
    purchaseLots: 'tests/fixtures/firstlot_demo/purchase_lots.csv',
    movement: 'tests/fixtures/firstlot_demo/movement.csv'
  },
  cogsSummary: [
    {
      sku: 'SKU-A',
      period: '2026-05',
      total_quantity_sold: 18,
      total_cogs: '210.00',
      average_unit_cost: '11.67'
    },
    {
      sku: 'SKU-B',
      period: '2026-05',
      total_quantity_sold: 2,
      total_cogs: '40.00',
      average_unit_cost: '20.00'
    }
  ],
  remainingLayers: [
    {
      lot_id: 'LOT-B-001',
      sku: 'SKU-B',
      received_date: '2026-05-03T00:00:00',
      original_quantity: 5,
      remaining_quantity: 3,
      unit_cost: '20.00',
      remaining_value: '60.00'
    }
  ],
  auditTrail: [
    {
      sale_id: 'SALE-001',
      sku: 'SKU-A',
      sale_date: '2026-05-15T00:00:00',
      lot_id: 'LOT-A-001',
      lot_received_date: '2026-05-01T00:00:00',
      quantity: 10,
      unit_cost: '11.00',
      total_cost: '110.00'
    },
    {
      sale_id: 'SALE-001',
      sku: 'SKU-A',
      sale_date: '2026-05-15T00:00:00',
      lot_id: 'LOT-A-002',
      lot_received_date: '2026-05-10T00:00:00',
      quantity: 2,
      unit_cost: '12.50',
      total_cost: '25.00'
    },
    {
      sale_id: 'SALE-002',
      sku: 'SKU-A',
      sale_date: '2026-05-20T00:00:00',
      lot_id: 'LOT-A-002',
      lot_received_date: '2026-05-10T00:00:00',
      quantity: 6,
      unit_cost: '12.50',
      total_cost: '75.00'
    },
    {
      sale_id: 'SALE-003',
      sku: 'SKU-B',
      sale_date: '2026-05-21T00:00:00',
      lot_id: 'LOT-B-001',
      lot_received_date: '2026-05-03T00:00:00',
      quantity: 2,
      unit_cost: '20.00',
      total_cost: '40.00'
    }
  ],
  shortfalls: [
    {
      sale_id: 'SALE-002',
      sku: 'SKU-A',
      sale_date: '2026-05-20T00:00:00',
      requested_quantity: 7,
      allocated_quantity: 6,
      shortfall_quantity: 1,
      available_quantity: 6,
      reason: 'INSUFFICIENT_INVENTORY',
      message: 'Insufficient inventory for SKU SKU-A. Needed: 7, Available: 6'
    }
  ]
};
