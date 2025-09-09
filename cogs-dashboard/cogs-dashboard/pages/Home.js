import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { runsService } from '../services/runs';
import StatusPill from '../components/StatusPill';
import toast from 'react-hot-toast';
import {
  ArrowUpTrayIcon,
  PlayIcon,
  DocumentIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

const Home = () => {
  const { tenantId } = useAuth();
  const [lastRun, setLastRun] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLastRun();
  }, [tenantId]);

  const loadLastRun = async () => {
    try {
      if (!tenantId) return;
      
      const response = await runsService.getRuns(tenantId, { limit: 1 });
      if (response.runs && response.runs.length > 0) {
        setLastRun(response.runs[0]);
      }
    } catch (error) {
      console.error('Failed to load last run:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!lastRun?.run_id) return;
    
    if (!window.confirm('Are you sure you want to rollback this run? This will restore inventory to its previous state.')) {
      return;
    }

    try {
      await runsService.rollbackRun(lastRun.run_id);
      toast.success('Run rolled back successfully');
      loadLastRun(); // Reload to show updated status
    } catch (error) {
      toast.error(error.message || 'Failed to rollback run');
    }
  };

  const quickActions = [
    {
      name: 'Upload Lots',
      description: 'Upload purchase lots CSV',
      href: '/upload?tab=lots',
      icon: ArrowUpTrayIcon,
      color: 'bg-blue-500'
    },
    {
      name: 'Upload Sales',
      description: 'Upload sales data CSV',
      href: '/upload?tab=sales',
      icon: DocumentIcon,
      color: 'bg-green-500'
    },
    {
      name: 'Run COGS',
      description: 'Execute FIFO calculation',
      href: '/runs/new',
      icon: PlayIcon,
      color: 'bg-purple-500'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-600">
          Welcome back! Here's what's happening with your FIFO COGS calculations.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {quickActions.map((action) => (
            <Link
              key={action.name}
              to={action.href}
              className="relative group bg-white p-6 focus-within:ring-2 focus-within:ring-inset focus-within:ring-blue-500 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <div>
                <span className={`rounded-lg inline-flex p-3 ${action.color} text-white`}>
                  <action.icon className="h-6 w-6" />
                </span>
              </div>
              <div className="mt-4">
                <h3 className="text-lg font-medium text-gray-900">
                  {action.name}
                </h3>
                <p className="mt-2 text-sm text-gray-500">
                  {action.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Last Run Card */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Last Run</h2>
          <Link
            to="/runs"
            className="text-sm text-blue-600 hover:text-blue-500"
          >
            View all runs →
          </Link>
        </div>

        {loading ? (
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ) : lastRun ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">
                    Run {lastRun.run_id.slice(0, 8)}
                  </span>
                  <StatusPill status={lastRun.status} />
                </div>
                <p className="text-sm text-gray-500">
                  {new Date(lastRun.started_at).toLocaleString()}
                </p>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-gray-900">
                  ${lastRun.total_cogs_calculated?.toFixed(2) || '0.00'}
                </div>
                <div className="text-sm text-gray-500">
                  {lastRun.total_sales_processed || 0} transactions
                </div>
              </div>
            </div>

            <div className="flex space-x-2">
              <Link
                to={`/runs/${lastRun.run_id}`}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                <ChartBarIcon className="h-4 w-4 mr-1" />
                View Details
              </Link>
              
              {lastRun.status === 'completed' && (
                <button
                  onClick={handleRollback}
                  className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                >
                  Rollback
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No runs yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by uploading your data and running a COGS calculation.
            </p>
            <div className="mt-6">
              <Link
                to="/upload"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <ArrowUpTrayIcon className="h-4 w-4 mr-2" />
                Upload Data
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;