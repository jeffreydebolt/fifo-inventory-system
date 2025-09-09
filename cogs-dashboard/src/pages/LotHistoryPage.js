import React, { useState, useEffect, useCallback } from 'react';
import { useClient } from '../contexts/ClientContext';

const LotHistoryPage = () => {
  const { client } = useClient();
  const [lots, setLots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('active'); // 'all', 'active', 'depleted'

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const loadLotHistory = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch real lot history from API
      const response = await fetch(`${API_BASE}/api/v1/runs/inventory/${client.client_id}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch lot history: ${response.status}`);
      }

      const data = await response.json();
      
      // Transform API data to match UI format
      const formattedLots = data.lots.map(lot => ({
        po_number: lot.lot_id || lot.po_number,
        sku: lot.sku,
        received_date: lot.received_date,
        original_quantity: lot.original_quantity,
        remaining_quantity: lot.remaining_quantity,
        unit_price: lot.unit_price,
        freight_cost_per_unit: lot.freight_cost_per_unit || 0,
        status: lot.remaining_quantity > 0 ? 'active' : 'depleted'
      }));

      // Sort by date descending
      formattedLots.sort((a, b) => new Date(b.received_date) - new Date(a.received_date));
      setLots(formattedLots);
      
    } catch (err) {
      setError(`Failed to load lot history: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    loadLotHistory();
  }, [loadLotHistory]);

  const filteredLots = lots.filter(lot => {
    switch (filter) {
      case 'active':
        return lot.remaining_quantity > 0;
      case 'depleted':
        return lot.remaining_quantity === 0;
      default:
        return true;
    }
  });

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const formatCurrency = (amount) => {
    return `$${amount.toFixed(2)}`;
  };

  const getStatusColor = (status) => {
    return status === 'active' ? '#10b981' : '#6b7280';
  };

  const getStatusText = (status, remaining) => {
    return remaining > 0 ? 'Active' : 'Depleted';
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f3f4f6' }}>
      {/* Header */}
      <header style={{
        backgroundColor: 'white',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        padding: '1rem 2rem'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              backgroundColor: '#10b981',
              color: 'white',
              padding: '0.5rem',
              borderRadius: '4px',
              fontWeight: 'bold',
              fontSize: '0.875rem'
            }}>
              [FL]
            </div>
            <h1 style={{ color: '#0f172a', margin: 0 }}>FirstLot</h1>
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Lot History</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: '#6b7280' }}>
              {client.company_name}
            </span>
            <button
              onClick={() => window.location.href = '/dashboard'}
              style={{
                backgroundColor: '#6b7280',
                color: 'white',
                padding: '0.5rem 1rem',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              ← Dashboard
            </button>
          </div>
        </div>
      </header>

      <main style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        {/* Page Header */}
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#0f172a', marginBottom: '0.5rem', fontSize: '1.5rem' }}>
            Lot History
          </h2>
          <p style={{ color: '#6b7280', margin: 0 }}>
            Track your inventory lots and their consumption using FIFO methodology
          </p>
        </div>

        {/* Filter Controls */}
        <div style={{
          backgroundColor: 'white',
          padding: '1rem 2rem',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          marginBottom: '2rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: '#374151', fontWeight: '500' }}>Filter by status:</span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {[
                { key: 'all', label: 'All' },
                { key: 'active', label: 'Active' },
                { key: 'depleted', label: 'Depleted' }
              ].map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  style={{
                    backgroundColor: filter === key ? '#10b981' : 'transparent',
                    color: filter === key ? 'white' : '#6b7280',
                    border: filter === key ? '1px solid #10b981' : '1px solid #d1d5db',
                    padding: '0.5rem 1rem',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div style={{ marginLeft: 'auto', color: '#6b7280', fontSize: '0.875rem' }}>
              Showing {filteredLots.length} of {lots.length} lots
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #fca5a5',
            color: '#dc2626',
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '2rem'
          }}>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>⚠️ Error</h3>
            <p style={{ margin: 0 }}>{error}</p>
          </div>
        )}

        {/* Lot History Table */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden'
        }}>
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
              <div style={{ color: '#6b7280' }}>Loading lot history...</div>
            </div>
          ) : filteredLots.length > 0 ? (
            <>
              <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid #e5e7eb' }}>
                <h3 style={{ color: '#0f172a', margin: 0 }}>Purchase Lots</h3>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f9fafb' }}>
                      <th style={{ textAlign: 'left', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>PO#</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>SKU</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>Date</th>
                      <th style={{ textAlign: 'right', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>Original Qty</th>
                      <th style={{ textAlign: 'right', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>Remaining</th>
                      <th style={{ textAlign: 'right', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>Unit Cost</th>
                      <th style={{ textAlign: 'center', padding: '0.75rem 1rem', color: '#374151', fontWeight: '600' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLots.map((lot, index) => (
                      <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ padding: '0.75rem 1rem', color: '#0f172a', fontFamily: 'monospace' }}>
                          {lot.po_number}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: '#0f172a', fontFamily: 'monospace' }}>
                          {lot.sku}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: '#6b7280' }}>
                          {formatDate(lot.received_date)}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: '#6b7280', textAlign: 'right' }}>
                          {lot.original_quantity.toLocaleString()}
                        </td>
                        <td style={{ 
                          padding: '0.75rem 1rem', 
                          color: lot.remaining_quantity > 0 ? '#10b981' : '#6b7280', 
                          textAlign: 'right',
                          fontWeight: '500'
                        }}>
                          {lot.remaining_quantity.toLocaleString()}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', color: '#6b7280', textAlign: 'right', fontFamily: 'monospace' }}>
                          {formatCurrency(lot.unit_price)}
                        </td>
                        <td style={{ padding: '0.75rem 1rem', textAlign: 'center' }}>
                          <span style={{
                            backgroundColor: lot.remaining_quantity > 0 ? '#d1fae5' : '#f3f4f6',
                            color: lot.remaining_quantity > 0 ? '#065f46' : '#6b7280',
                            padding: '0.25rem 0.75rem',
                            borderRadius: '12px',
                            fontSize: '0.75rem',
                            fontWeight: '500'
                          }}>
                            {getStatusText(lot.status, lot.remaining_quantity)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📦</div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>No Lots Found</h3>
              <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
                {filter === 'active' ? 'No active lots found.' :
                 filter === 'depleted' ? 'No depleted lots found.' :
                 'No lots have been uploaded yet.'}
              </p>
              {lots.length === 0 && (
                <button
                  onClick={() => window.location.href = '/upload'}
                  style={{
                    backgroundColor: '#10b981',
                    color: 'white',
                    padding: '0.75rem 2rem',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: '600'
                  }}
                >
                  Upload Your First Lots
                </button>
              )}
            </div>
          )}
        </div>

        {/* Summary Stats */}
        {filteredLots.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '1rem',
            marginTop: '2rem'
          }}>
            <StatCard
              title="Active Lots"
              value={lots.filter(l => l.remaining_quantity > 0).length}
              color="#10b981"
            />
            <StatCard
              title="Depleted Lots"
              value={lots.filter(l => l.remaining_quantity === 0).length}
              color="#6b7280"
            />
            <StatCard
              title="Total Remaining Value"
              value={formatCurrency(lots.reduce((sum, lot) => 
                sum + (lot.remaining_quantity * lot.unit_price), 0))}
              color="#3b82f6"
            />
            <StatCard
              title="Average Cost per Unit"
              value={formatCurrency(lots.length > 0 ? 
                lots.reduce((sum, lot) => sum + lot.unit_price, 0) / lots.length : 0)}
              color="#8b5cf6"
            />
          </div>
        )}
      </main>
    </div>
  );
};

const StatCard = ({ title, value, color }) => (
  <div style={{
    backgroundColor: 'white',
    padding: '1.5rem',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    textAlign: 'center'
  }}>
    <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: color, marginBottom: '0.5rem' }}>
      {value}
    </div>
    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
      {title}
    </div>
  </div>
);

export default LotHistoryPage;