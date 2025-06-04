
import { api } from '@/lib/api';
import { Product, Unit, ProductDelivery } from '@/types/products';

export const productService = {
  async getProducts(params?: {
    skip?: number;
    limit?: number;
    name_filter?: string;
    low_stock_only?: boolean;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.name_filter) queryParams.append('name_filter', params.name_filter);
    if (params?.low_stock_only !== undefined) queryParams.append('low_stock_only', params.low_stock_only.toString());

    const response = await api.get(`/api/products/?${queryParams}`);
    return response.data;
  },

  async getProduct(productId: number): Promise<Product> {
    const response = await api.get(`/api/products/${productId}`);
    return response.data;
  },

  async createProduct(productData: {
    name: string;
    unit_id: number;
    min_quantity: number;
  }): Promise<Product> {
    const response = await api.post('/api/products/', productData);
    return response.data;
  },

  async updateProduct(productId: number, productData: {
    name: string;
    unit_id: number;
    min_quantity: number;
  }): Promise<Product> {
    const response = await api.put(`/api/products/${productId}`, productData);
    return response.data;
  },

  async deleteProduct(productId: number): Promise<Product> {
    const response = await api.delete(`/api/products/${productId}`);
    return response.data;
  },

  async getUnits(skip = 0, limit = 100): Promise<Unit[]> {
    const response = await api.get(`/api/products/units/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async createUnit(unitData: {
    name: string;
    short_name: string;
  }): Promise<Unit> {
    const response = await api.post('/api/products/units/', unitData);
    return response.data;
  },

  async getDeliveries(params?: {
    product_id?: number;
    skip?: number;
    limit?: number;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.product_id !== undefined) queryParams.append('product_id', params.product_id.toString());
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());

    const response = await api.get(`/api/products/deliveries/?${queryParams}`);
    return response.data;
  },

  async getAllDeliveries(params?: {
    product_id?: number;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.product_id !== undefined) queryParams.append('product_id', params.product_id.toString());
    // Get all deliveries without limit
    queryParams.append('limit', '1000');

    const response = await api.get(`/api/products/deliveries/?${queryParams}`);
    return response.data;
  },

  async createDelivery(deliveryData: {
    product_id: number;
    quantity: number;
    delivery_date: string;
    supplier: string;
    price: number;
  }): Promise<ProductDelivery> {
    const response = await api.post('/api/products/deliveries/', deliveryData);
    return response.data;
  }
};
