
import { api } from '@/lib/api';

export const deliveryService = {
  async createDelivery(deliveryData: {
    product_id: number;
    quantity: number;
    supplier: string;
    notes?: string;
  }) {
    const response = await api.post('/api/products/deliveries/', deliveryData);
    return response.data;
  },

  async getDeliveries(skip: number = 0, limit: number = 100) {
    const response = await api.get(`/api/products/deliveries/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async getAllDeliveries() {
    const response = await api.get('/api/products/deliveries/?limit=1000');
    return response.data;
  }
};
