
import { api } from '@/lib/api';

export const notificationService = {
  async getNotifications(params?: {
    skip?: number;
    limit?: number;
    unread_only?: boolean;
  }) {
    const queryParams = new URLSearchParams();
    if (params?.skip !== undefined) queryParams.append('skip', params.skip.toString());
    if (params?.limit !== undefined) queryParams.append('limit', params.limit.toString());
    if (params?.unread_only !== undefined) queryParams.append('unread_only', params.unread_only.toString());

    const response = await api.get(`/api/notifications/?${queryParams}`);
    return response.data;
  },

  async markAsRead(notificationId: number) {
    const response = await api.post(`/api/notifications/${notificationId}/mark-as-read`);
    return response.data;
  },

  async markAllAsRead() {
    const response = await api.post('/api/notifications/mark-all-as-read');
    return response.data;
  }
};
