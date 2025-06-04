
import { api } from '@/lib/api';

export const userService = {
  async getUser(userId: number) {
    const response = await api.get(`/api/users/${userId}`);
    return response.data;
  },

  async getUsers(skip = 0, limit = 12) { // Backend maksimal limit ni hurmat qilish
    const response = await api.get(`/api/users/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async getCurrentUser() {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  async createUser(userData: {
    username: string;
    full_name: string;
    password: string;
    role_id: number;
  }) {
    const response = await api.post('/api/users/', userData);
    return response.data;
  },

  async updateUser(userId: number, userData: {
    username: string;
    full_name: string;
    role_id: number;
    is_active: boolean;
  }) {
    const response = await api.put(`/api/users/${userId}`, userData);
    return response.data;
  },

  async deleteUser(userId: number) {
    const response = await api.delete(`/api/users/${userId}`);
    return response.data;
  },

  async createRole(roleData: {
    name: string;
    description?: string;
  }) {
    const response = await api.post('/api/users/roles/', roleData);
    return response.data;
  },

  async getRoles(skip = 0, limit = 12) { // Backend maksimal limit ni hurmat qilish
    const response = await api.get(`/api/users/roles/?skip=${skip}&limit=${limit}`);
    return response.data;
  }
};
