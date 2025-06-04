
import { api } from '@/lib/api';

export const auditService = {
  async getAuditLogs(skip = 0, limit = 50) { // Backend limit ga mos
    const response = await api.get(`/api/audit-logs/?skip=${skip}&limit=${limit}`);
    return response.data;
  }
};
