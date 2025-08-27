import React, { useState, useEffect } from 'react';
import { useClient } from '../contexts/ClientContext';

const MonthlyCogsPage = () => {
  const { client } = useClient();
  const [monthlyCogs, setMonthlyCogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    loadMonthlyCogs();
  }, [client]);

  const loadMonthlyCogs = async () => {
    try {
      setLoading(true);
      // For now, simulate data - in production this would call your backend
      const mockData = [
        {
          month: 'November 2024',
          sales: 142234,
          cogs: 48234,
          cogs_percentage: 34.2,
          change: 2.1,
          trend: 'up'
        },
        {
          month: 'October 2024',
          sales: 135456,
          cogs: 42386,
          cogs_percentage: 32.1,
          change: -0.5,
          trend: 'down'
        },
        {
          month: 'September 2024',
          sales: 128900,
          cogs: 41448,
          cogs_percentage: 32.6,
          change: null,
          trend: 'none'
        },
        {
          month: 'August 2024',
          sales: 118500,
          cogs: 38640,
          cogs_percentage: 32.6,
          change: 1.2,
          trend: 'up'
        },
        {
          month: 'July 2024',
          sales: 112300,
          cogs: 36142,
          cogs_percentage: 32.2,
          change: -0.8,
          trend: 'down'
        },
        {
          month: 'June 2024',
          sales: 105800,
          cogs: 34914,
          cogs_percentage: 33.0,
          change: 0.3,
          trend: 'up'
        }
      ];

      setMonthlyCogs(mockData);
      
    } catch (err) {
      setError(`Failed to load monthly COGS data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return `$${amount.toLocaleString()}`;
  };

  const formatPercentage = (percentage) => {
    return `${percentage.toFixed(1)}%`;
  };

  const getChangeIcon = (trend, change) => {
    if (change === null) return '--';
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '--';
  };

  const getChangeColor = (trend, change) => {
    if (change === null) return '#6b7280';
    // For COGS percentage, down is good (green), up is bad (red)
    if (trend === 'down') return '#10b981';
    if (trend === 'up') return '#ef4444';
    return '#6b7280';
  };

  const getChangeText = (change) => {
    if (change === null) return '--';
    return `${Math.abs(change).toFixed(1)}%`;
  };

  const calculateTotals = () => {
    const totalSales = monthlyCogs.reduce((sum, month) => sum + month.sales, 0);
    const totalCogs = monthlyCogs.reduce((sum, month) => sum + month.cogs, 0);
    const avgCogsPercentage = monthlyCogs.length > 0 ? 
      monthlyCogs.reduce((sum, month) => sum + month.cogs_percentage, 0) / monthlyCogs.length : 0;
    
    return { totalSales, totalCogs, avgCogsPercentage };
  };

  const { totalSales, totalCogs, avgCogsPercentage } = calculateTotals();

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
            <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>Monthly COGS</span>
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
            Monthly COGS Summary
          </h2>
          <p style={{ color: '#6b7280', margin: 0 }}>
            Track your cost of goods sold trends and performance over time
          </p>
        </div>

        {/* Summary Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          <SummaryCard
            title="Total Sales (6 months)"
            value={formatCurrency(totalSales)}
            subtitle="Revenue from processed periods"
            color="#3b82f6"
          />
          <SummaryCard
            title="Total COGS (6 months)"
            value={formatCurrency(totalCogs)}
            subtitle="Cost of goods sold"
            color="#8b5cf6"
          />
          <SummaryCard
            title="Average COGS %"
            value={formatPercentage(avgCogsPercentage)}
            subtitle="Average cost percentage"
            color="#10b981"
          />
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

        {/* Monthly COGS Table */}
        <div style={{
          backgroundColor: 'white',
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden'
        }}>
          {loading ? (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
              <div style={{ color: '#6b7280' }}>Loading monthly COGS data...</div>
            </div>
          ) : monthlyCogs.length > 0 ? (
            <>
              <div style={{ padding: '1.5rem 2rem', borderBottom: '1px solid #e5e7eb' }}>
                <h3 style={{ color: '#0f172a', margin: 0 }}>Monthly Performance</h3>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f9fafb' }}>
                      <th style={{ textAlign: 'left', padding: '1rem 1.5rem', color: '#374151', fontWeight: '600' }}>Month</th>
                      <th style={{ textAlign: 'right', padding: '1rem 1.5rem', color: '#374151', fontWeight: '600' }}>Sales</th>
                      <th style={{ textAlign: 'right', padding: '1rem 1.5rem', color: '#374151', fontWeight: '600' }}>COGS</th>
                      <th style={{ textAlign: 'right', padding: '1rem 1.5rem', color: '#374151', fontWeight: '600' }}>COGS %</th>
                      <th style={{ textAlign: 'center', padding: '1rem 1.5rem', color: '#374151', fontWeight: '600' }}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyCogs.map((month, index) => (
                      <tr key={index} style={{ borderBottom: '1px solid #f3f4f6' }}>
                        <td style={{ 
                          padding: '1rem 1.5rem', 
                          color: '#0f172a',
                          fontWeight: '500'
                        }}>
                          {month.month}
                        </td>
                        <td style={{ 
                          padding: '1rem 1.5rem', 
                          color: '#6b7280', 
                          textAlign: 'right',
                          fontFamily: 'monospace'
                        }}>
                          {formatCurrency(month.sales)}
                        </td>
                        <td style={{ 
                          padding: '1rem 1.5rem', 
                          color: '#6b7280', 
                          textAlign: 'right',
                          fontFamily: 'monospace'
                        }}>
                          {formatCurrency(month.cogs)}
                        </td>
                        <td style={{ 
                          padding: '1rem 1.5rem', 
                          color: '#0f172a', 
                          textAlign: 'right',
                          fontWeight: '600',
                          fontSize: '1rem'
                        }}>
                          {formatPercentage(month.cogs_percentage)}
                        </td>
                        <td style={{ 
                          padding: '1rem 1.5rem', 
                          textAlign: 'center'
                        }}>
                          <div style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            color: getChangeColor(month.trend, month.change),
                            fontWeight: '500'
                          }}>
                            <span style={{ fontSize: '1rem' }}>
                              {getChangeIcon(month.trend, month.change)}
                            </span>
                            <span>{getChangeText(month.change)}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div style={{ padding: '3rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📊</div>
              <h3 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>No COGS Data Found</h3>
              <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
                Process some FIFO calculations to see your monthly COGS trends.
              </p>
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
                Process Your First FIFO Run
              </button>
            </div>
          )}
        </div>

        {/* Insights Section */}
        {monthlyCogs.length > 0 && (
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '8px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
            marginTop: '2rem'
          }}>
            <h3 style={{ color: '#0f172a', marginBottom: '1rem' }}>📈 Key Insights</h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
              gap: '1rem'
            }}>
              <InsightCard
                title="Best Month"
                value={monthlyCogs.reduce((best, month) => 
                  month.cogs_percentage < best.cogs_percentage ? month : best
                ).month}
                subtitle={`Lowest COGS: ${formatPercentage(
                  monthlyCogs.reduce((best, month) => 
                    month.cogs_percentage < best.cogs_percentage ? month : best
                  ).cogs_percentage
                )}`}
                color="#10b981"
              />
              <InsightCard
                title="Highest Sales Month"
                value={monthlyCogs.reduce((highest, month) => 
                  month.sales > highest.sales ? month : highest
                ).month}
                subtitle={`Sales: ${formatCurrency(
                  monthlyCogs.reduce((highest, month) => 
                    month.sales > highest.sales ? month : highest
                  ).sales
                )}`}
                color="#3b82f6"
              />
              <InsightCard
                title="COGS Trend"
                value={monthlyCogs[0].cogs_percentage > monthlyCogs[monthlyCogs.length-1].cogs_percentage 
                  ? "Improving" : "Increasing"}
                subtitle={`${Math.abs(monthlyCogs[0].cogs_percentage - monthlyCogs[monthlyCogs.length-1].cogs_percentage).toFixed(1)}% ${
                  monthlyCogs[0].cogs_percentage > monthlyCogs[monthlyCogs.length-1].cogs_percentage ? 'decrease' : 'increase'
                } from 6 months ago`}
                color={monthlyCogs[0].cogs_percentage > monthlyCogs[monthlyCogs.length-1].cogs_percentage ? "#10b981" : "#ef4444"}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

const SummaryCard = ({ title, value, subtitle, color }) => (
  <div style={{
    backgroundColor: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    textAlign: 'center'
  }}>
    <div style={{ fontSize: '2rem', fontWeight: 'bold', color: color, marginBottom: '0.5rem' }}>
      {value}
    </div>
    <div style={{ fontSize: '1rem', color: '#0f172a', fontWeight: '500', marginBottom: '0.25rem' }}>
      {title}
    </div>
    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
      {subtitle}
    </div>
  </div>
);

const InsightCard = ({ title, value, subtitle, color }) => (
  <div style={{
    backgroundColor: '#f9fafb',
    padding: '1.5rem',
    borderRadius: '6px',
    borderLeft: `4px solid ${color}`
  }}>
    <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
      {title}
    </div>
    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#0f172a', marginBottom: '0.25rem' }}>
      {value}
    </div>
    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
      {subtitle}
    </div>
  </div>
);

export default MonthlyCogsPage;