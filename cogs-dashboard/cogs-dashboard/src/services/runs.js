import api from './api';

export const runsService = {
  // Get all runs for a tenant
  async getRuns(tenantId, params = {}) {
    const response = await api.get('/api/v1/runs', {
      params: { tenant_id: tenantId, ...params }
    });
    return response.data;
  },

  // Get a specific run
  async getRun(runId) {
    const response = await api.get(`/api/v1/runs/${runId}`);
    return response.data;
  },

  // Create and execute a new run
  async createRun(data) {
    const response = await api.post('/api/v1/runs', data);
    return response.data;
  },

  // Rollback a run
  async rollbackRun(runId) {
    const response = await api.post(`/api/v1/runs/${runId}/rollback`);
    return response.data;
  },

  // Get journal entry for a run
  async getJournalEntry(runId, format = 'csv') {
    const response = await api.get(`/api/v1/runs/${runId}/journal-entry`, {
      params: { format }
    });
    return response.data;
  },

  // Upload lots file
  async uploadLots(tenantId, file) {
    const formData = new FormData();
    formData.append('tenant_id', tenantId);
    formData.append('file', file);

    const response = await api.post('/api/v1/files/lots', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Upload sales file
  async uploadSales(tenantId, file) {
    const formData = new FormData();
    formData.append('tenant_id', tenantId);
    formData.append('file', file);

    const response = await api.post('/api/v1/files/sales', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get CSV templates
  async getLotsTemplate() {
    const response = await api.get('/api/v1/files/templates/lots', {
      responseType: 'blob'
    });
    return response.data;
  },

  async getSalesTemplate() {
    const response = await api.get('/api/v1/files/templates/sales', {
      responseType: 'blob'
    });
    return response.data;
  }
};