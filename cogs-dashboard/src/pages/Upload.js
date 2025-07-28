import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { runsService } from '../services/runs';
import toast from 'react-hot-toast';
import {
  ArrowUpTrayIcon,
  DocumentArrowDownIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

const Upload = () => {
  const { tenantId } = useAuth();
  const [activeTab, setActiveTab] = useState('lots');
  const [lotsFile, setLotsFile] = useState(null);
  const [salesFile, setSalesFile] = useState(null);
  const [lotsUploading, setLotsUploading] = useState(false);
  const [salesUploading, setSalesUploading] = useState(false);
  const [lotsUploaded, setLotsUploaded] = useState(false);
  const [salesUploaded, setSalesUploaded] = useState(false);

  const handleLotsUpload = async () => {
    if (!lotsFile) {
      toast.error('Please select a file to upload');
      return;
    }

    setLotsUploading(true);
    try {
      const result = await runsService.uploadLots(tenantId, lotsFile);
      toast.success(`Uploaded ${result.rows_count} lots successfully`);
      setLotsUploaded(true);
    } catch (error) {
      toast.error(error.message || 'Failed to upload lots');
    } finally {
      setLotsUploading(false);
    }
  };

  const handleSalesUpload = async () => {
    if (!salesFile) {
      toast.error('Please select a file to upload');
      return;
    }

    setSalesUploading(true);
    try {
      const result = await runsService.uploadSales(tenantId, salesFile);
      toast.success(`Uploaded ${result.rows_count} sales records successfully`);
      setSalesUploaded(true);
    } catch (error) {
      toast.error(error.message || 'Failed to upload sales');
    } finally {
      setSalesUploading(false);
    }
  };

  const downloadTemplate = async (type) => {
    try {
      const blob = await (type === 'lots' 
        ? runsService.getLotsTemplate() 
        : runsService.getSalesTemplate()
      );
      
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}_template.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      toast.success(`${type} template downloaded`);
    } catch (error) {
      toast.error(`Failed to download ${type} template`);
    }
  };

  const tabs = [
    { id: 'lots', name: 'Purchase Lots', count: lotsUploaded ? '✓' : null },
    { id: 'sales', name: 'Sales Data', count: salesUploaded ? '✓' : null },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Data</h1>
        <p className="mt-1 text-sm text-gray-600">
          Upload your purchase lots and sales data to run FIFO COGS calculations.
        </p>
      </div>

      {/* Upload Status */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Upload Status</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex items-center space-x-3">
            {lotsUploaded ? (
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
            ) : (
              <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
            )}
            <span className={`text-sm ${lotsUploaded ? 'text-green-700' : 'text-gray-500'}`}>
              Purchase Lots {lotsUploaded ? 'Uploaded' : 'Pending'}
            </span>
          </div>
          <div className="flex items-center space-x-3">
            {salesUploaded ? (
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
            ) : (
              <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
            )}
            <span className={`text-sm ${salesUploaded ? 'text-green-700' : 'text-gray-500'}`}>
              Sales Data {salesUploaded ? 'Uploaded' : 'Pending'}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  border-b-2 py-4 px-1 text-sm font-medium whitespace-nowrap
                  ${activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }
                `}
              >
                {tab.name}
                {tab.count && (
                  <span className="ml-2 bg-green-100 text-green-800 text-xs rounded-full px-2 py-1">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'lots' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Purchase Lots</h3>
                <p className="mt-1 text-sm text-gray-600">
                  Upload a CSV file containing your purchase lot data including lot IDs, SKUs, 
                  quantities, costs, and received dates.
                </p>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={() => downloadTemplate('lots')}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                  Download Template
                </button>
              </div>

              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
                <div className="text-center">
                  <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <div className="mt-4">
                    <label htmlFor="lots-file" className="cursor-pointer">
                      <span className="text-sm font-medium text-blue-600 hover:text-blue-500">
                        Choose a file
                      </span>
                      <input
                        id="lots-file"
                        type="file"
                        accept=".csv"
                        className="sr-only"
                        onChange={(e) => setLotsFile(e.target.files[0])}
                      />
                    </label>
                    <p className="text-sm text-gray-500">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">CSV files only</p>
                </div>
              </div>

              {lotsFile && (
                <div className="bg-gray-50 rounded-md p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{lotsFile.name}</p>
                      <p className="text-sm text-gray-500">{(lotsFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={handleLotsUpload}
                      disabled={lotsUploading}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      {lotsUploading ? 'Uploading...' : 'Upload'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'sales' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900">Sales Data</h3>
                <p className="mt-1 text-sm text-gray-600">
                  Upload a CSV file containing your sales transactions including SKUs, quantities, 
                  and sale dates.
                </p>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={() => downloadTemplate('sales')}
                  className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                >
                  <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
                  Download Template
                </button>
              </div>

              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6">
                <div className="text-center">
                  <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <div className="mt-4">
                    <label htmlFor="sales-file" className="cursor-pointer">
                      <span className="text-sm font-medium text-blue-600 hover:text-blue-500">
                        Choose a file
                      </span>
                      <input
                        id="sales-file"
                        type="file"
                        accept=".csv"
                        className="sr-only"
                        onChange={(e) => setSalesFile(e.target.files[0])}
                      />
                    </label>
                    <p className="text-sm text-gray-500">or drag and drop</p>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">CSV files only</p>
                </div>
              </div>

              {salesFile && (
                <div className="bg-gray-50 rounded-md p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{salesFile.name}</p>
                      <p className="text-sm text-gray-500">{(salesFile.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={handleSalesUpload}
                      disabled={salesUploading}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                    >
                      {salesUploading ? 'Uploading...' : 'Upload'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Next Steps */}
      {lotsUploaded && salesUploaded && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex">
            <CheckCircleIcon className="h-5 w-5 text-green-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Ready to Run COGS</h3>
              <p className="mt-2 text-sm text-green-700">
                Both lots and sales data have been uploaded. You can now run a FIFO COGS calculation.
              </p>
              <div className="mt-4">
                <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700">
                  Run COGS Calculation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;