
import { api } from '@/lib/api';

export const reportService = {
  async generateMonthlyReport(year: number, month: number) {
    const response = await api.post(`/api/reports/monthly/generate?year=${year}&month=${month}`);
    return response.data;
  },

  async getMonthlyReports(skip = 0, limit = 100) {
    const response = await api.get(`/api/reports/monthly/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async getMonthlyReport(reportId: number) {
    const response = await api.get(`/api/reports/monthly/${reportId}`);
    return response.data;
  },

  async getIngredientConsumptionData(startDate: string, endDate: string) {
    const response = await api.get(`/api/reports/visualization/ingredient-consumption?start_date=${startDate}&end_date=${endDate}`);
    return response.data;
  },

  async getProductDeliveryTrends(startDate: string, endDate: string) {
    const response = await api.get(`/api/reports/visualization/product-delivery-trends?start_date=${startDate}&end_date=${endDate}`);
    return response.data;
  }
};
