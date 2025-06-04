
export interface NotificationType {
  id: number;
  name: string;
  description: string;
}

export interface Notification {
  id: number;
  message: string;
  notification_type_id: number;
  user_id: number | null;
  notification_type: NotificationType;
  user: {
    username: string;
    full_name: string;
  } | null;
  is_read: boolean;
  created_at: string;
}
