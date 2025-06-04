
import { api } from '@/lib/api';
import { User, Role } from '@/types/auth';

export const authService = {
  async setupInitialData() {
    const response = await api.post('/api/auth/setup-initial-data');
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get('/api/auth/me');
    return response.data;
  }
};

export const userService = {
  async getUsers(skip = 0, limit = 100) {
    const response = await api.get(`/api/users/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async getUser(userId: number): Promise<User> {
    const response = await api.get(`/api/users/${userId}`);
    return response.data;
  },

  async createUser(userData: {
    username: string;
    full_name: string;
    password: string;
    role_id: number;
  }): Promise<User> {
    const response = await api.post('/api/users/', userData);
    return response.data;
  },

  async updateUser(userId: number, userData: {
    username: string;
    full_name: string;
    password?: string;
    role_id: number;
    is_active: boolean;
  }): Promise<User> {
    const response = await api.put(`/api/users/${userId}`, userData);
    return response.data;
  },

  async deleteUser(userId: number): Promise<User> {
    const response = await api.delete(`/api/users/${userId}`);
    return response.data;
  },

  async getRoles(skip = 0, limit = 20): Promise<Role[]> {
    const response = await api.get(`/api/users/roles/?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  async getRole(roleId: number): Promise<Role> {
    const response = await api.get(`/api/users/roles/${roleId}`);
    return response.data;
  },

  async createRole(roleData: {
    name: string;
    description: string;
  }): Promise<Role> {
    const response = await api.post('/api/users/roles/', roleData);
    return response.data;
  }
};
