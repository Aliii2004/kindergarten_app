
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Bell, AlertTriangle, Check, CheckCheck, Activity, Calendar } from 'lucide-react';
import { api } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuth } from '@/hooks/useAuth';
import { auditService } from '@/services/auditService';

interface Notification {
  id: number;
  message: string;
  notification_type_id: number;
  user_id: number | null;
  notification_type: {
    id: number;
    name: string;
    description: string;
  };
  user: {
    username: string;
    full_name: string;
  } | null;
  is_read: boolean;
  created_at: string;
}

const NotificationsPage = () => {
  const [showOnlyUnread, setShowOnlyUnread] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role.name === 'admin';
  
  // WebSocket connection for real-time notifications
  const { messages: wsMessages, isConnected } = useWebSocket();

  // Fetch notifications
  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications', showOnlyUnread],
    queryFn: async () => {
      const response = await api.get(`/api/notifications/?unread_only=${showOnlyUnread}&limit=100`);
      return response.data;
    }
  });

  // Fetch audit logs - faqat admin uchun
  const { data: auditLogs = [], isLoading: auditLoading } = useQuery({
    queryKey: ['audit-logs-notifications'],
    queryFn: () => auditService.getAuditLogs(0, 20),
    enabled: isAdmin
  });

  // Mark as read mutation
  const markAsReadMutation = useMutation({
    mutationFn: async (notificationId: number) => {
      const response = await api.post(`/api/notifications/${notificationId}/mark-as-read`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Bildirishnoma o'qilgan deb belgilandi"
      });
    },
    onError: () => {
      toast({
        title: "Xatolik",
        description: "Bildirishnomani belgilashda xatolik",
        variant: "destructive"
      });
    }
  });

  // Mark all as read mutation
  const markAllAsReadMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post('/api/notifications/mark-all-as-read');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Barcha bildirishnomalar o'qilgan deb belgilandi"
      });
    },
    onError: () => {
      toast({
        title: "Xatolik",
        description: "Bildirishnomalarni belgilashda xatolik",
        variant: "destructive"
      });
    }
  });

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'low_stock':
        return <AlertTriangle className="h-5 w-5 text-orange-500" />;
      default:
        return <Bell className="h-5 w-5 text-blue-500" />;
    }
  };

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'low_stock':
        return 'border-orange-200 bg-orange-50';
      default:
        return 'border-blue-200 bg-blue-50';
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Noma\'lum sana';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Noma\'lum sana';
      return date.toLocaleDateString('uz-UZ', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return 'Noma\'lum sana';
    }
  };

  const unreadCount = notifications.filter((n: Notification) => !n.is_read).length;

  if (isLoading || (isAdmin && auditLoading)) {
    return (
      <div className="p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Yuklanmoqda...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <Bell className="h-8 w-8 mr-3" />
            Bildirishnomalar
            {unreadCount > 0 && (
              <Badge className="ml-2 bg-red-500">{unreadCount}</Badge>
            )}
          </h1>
          <p className="text-gray-600">Tizim bildirishnomalari va ogohlantirishlar</p>
        </div>
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <Button 
              onClick={() => markAllAsReadMutation.mutate()}
              variant="outline"
            >
              <CheckCheck className="h-4 w-4 mr-2" />
              Barchasini O'qilgan Deb Belgilash
            </Button>
          )}
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filtrlar</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Switch
              id="unread-only"
              checked={showOnlyUnread}
              onCheckedChange={setShowOnlyUnread}
            />
            <label htmlFor="unread-only" className="text-sm font-medium">
              Faqat o'qilmagan bildirishnomalar
            </label>
          </div>
        </CardContent>
      </Card>

      {/* WebSocket Status */}
      <Card className={isConnected ? "border-green-200 bg-green-50" : "border-yellow-200 bg-yellow-50"}>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`}></div>
            <span className={`text-sm ${isConnected ? 'text-green-700' : 'text-yellow-700'}`}>
              {isConnected ? 'Real-vaqt bildirishnomalar faol' : 'Real-vaqt bildirishnomalar o\'chiq'}
            </span>
            {wsMessages.length > 0 && (
              <Badge variant="secondary" className="ml-2">
                {wsMessages.length} yangi xabar
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs - Faqat admin uchun */}
      {isAdmin && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Activity className="h-5 w-5 mr-2" />
              Audit Loglar (Tizim Faoliyatlari)
            </CardTitle>
            <CardDescription>
              Tizimda amalga oshirilgan barcha amallar ro'yxati
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {auditLogs.length === 0 ? (
                <div className="text-center py-4 text-gray-500">
                  <Activity className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Audit loglar yo'q</p>
                </div>
              ) : (
                auditLogs.map((log: any) => (
                  <div key={log.id} className="flex items-center space-x-3 text-sm p-3 border rounded bg-gray-50">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-gray-900 font-medium">{log.action || 'Faoliyat'}</p>
                      <p className="text-gray-600">
                        Foydalanuvchi: {log.user?.full_name || 'Noma\'lum foydalanuvchi'}
                      </p>
                      {log.table_name && (
                        <p className="text-gray-500 text-xs">Jadval: {log.table_name}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="text-gray-400 text-xs">
                        {formatDate(log.timestamp)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications List */}
      <div className="space-y-4">
        {notifications.length === 0 ? (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center text-gray-500">
                <Bell className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Bildirishnomalar yo'q</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          notifications.map((notification: Notification) => (
            <Card 
              key={notification.id}
              className={`${
                !notification.is_read 
                  ? getNotificationColor(notification.notification_type.name) 
                  : 'border-gray-200'
              } ${!notification.is_read ? 'shadow-md' : ''}`}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    {getNotificationIcon(notification.notification_type.name)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="secondary" className="text-xs">
                          {notification.notification_type.name}
                        </Badge>
                        {!notification.is_read && (
                          <Badge className="bg-blue-500 text-xs">Yangi</Badge>
                        )}
                      </div>
                      <p className={`${!notification.is_read ? 'font-medium' : ''} text-gray-900`}>
                        {notification.message}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                        <span>
                          {formatDate(notification.created_at)}
                        </span>
                        {notification.user && (
                          <span>
                            Foydalanuvchi: {notification.user.full_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    {!notification.is_read && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => markAsReadMutation.mutate(notification.id)}
                      >
                        <Check className="h-3 w-3 mr-1" />
                        O'qilgan
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Recent WebSocket Messages - faqat ulanishda ko'rsatish */}
      {isConnected && wsMessages.length > 0 && (
        <Card className="border-purple-200 bg-purple-50">
          <CardHeader>
            <CardTitle className="text-lg text-purple-700">
              Real-vaqt Xabarlar (WebSocket)
            </CardTitle>
            <CardDescription>
              So'nggi real-vaqt xabarlar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-60 overflow-y-auto">
              {wsMessages.slice(-5).map((message, index) => (
                <div key={index} className="bg-white p-2 rounded border text-sm">
                  <div className="text-xs text-gray-500 mb-1">
                    {new Date().toLocaleTimeString()}
                  </div>
                  <div className="text-sm">
                    Type: {message.type}
                  </div>
                  {message.data && (
                    <div className="text-xs text-gray-600 mt-1 max-h-20 overflow-auto">
                      {JSON.stringify(message.data, null, 2)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default NotificationsPage;
