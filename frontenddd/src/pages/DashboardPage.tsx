
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { Users, Package, ChefHat, TrendingUp, AlertTriangle, Activity } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { productService } from '@/services/productService';
import { notificationService } from '@/services/notificationService';
import { reportService } from '@/services/reportService';

const DashboardPage = () => {
  const { user } = useAuth();

  // Fetch products for stock alerts - only for admin and menejer
  const { data: products = [] } = useQuery({
    queryKey: ['products'],
    queryFn: () => productService.getProducts(),
    enabled: user?.role.name !== 'oshpaz'
  });

  // Fetch notifications
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationService.getNotifications({ limit: 5, unread_only: true })
  });

  // Fetch chart data for last 30 days - only for admin and menejer
  const endDate = new Date().toISOString().split('T')[0];
  const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  const { data: ingredientConsumption = [] } = useQuery({
    queryKey: ['ingredient-consumption', startDate, endDate],
    queryFn: () => reportService.getIngredientConsumptionData(startDate, endDate),
    enabled: user?.role.name !== 'oshpaz'
  });

  const { data: deliveryTrends = [] } = useQuery({
    queryKey: ['delivery-trends', startDate, endDate],
    queryFn: () => reportService.getProductDeliveryTrends(startDate, endDate),
    enabled: user?.role.name !== 'oshpaz'
  });

  // Calculate statistics - only for admin and menejer
  const lowStockProducts = user?.role.name !== 'oshpaz' ? products.filter((product: any) => {
    // current_quantity mavjud bo'lsa uni ishlatamiz, aks holda quantity ni ishlatamiz
    const currentQuantity = product.current_quantity !== undefined ? product.current_quantity : product.quantity || 0;
    const minQuantity = product.min_quantity || product.min_stock_level || 0;
    return currentQuantity <= minQuantity;
  }) : [];
  const totalProducts = user?.role.name !== 'oshpaz' ? products.length : 0;
  const unreadNotifications = notifications.length;

  // Prepare chart data - only for admin and menejer
  const stockStatusData = user?.role.name !== 'oshpaz' ? [
    { name: 'Yetarli mahsulotlar', value: totalProducts - lowStockProducts.length, color: '#10B981' },
    { name: 'Kam qolgan mahsulotlar', value: lowStockProducts.length, color: '#EF4444' }
  ] : [];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Bog'cha boshqaruv tizimi</p>
        {user && (
          <p className="text-sm text-gray-500 mt-1">
            Xush kelibsiz, {user.full_name} ({user.role.name})
          </p>
        )}
      </div>

      {/* Stats Cards - Different for chef */}
      {user?.role.name === 'oshpaz' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">O'qilmagan Bildirishnomalar</p>
                  <p className="text-2xl font-bold text-orange-600">{unreadNotifications}</p>
                </div>
                <Activity className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Sizning Rolingiz</p>
                  <p className="text-2xl font-bold text-green-600">Oshpaz</p>
                </div>
                <ChefHat className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Tizim Holati</p>
                  <p className="text-2xl font-bold text-blue-600">Faol</p>
                </div>
                <TrendingUp className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Jami Mahsulotlar</p>
                  <p className="text-2xl font-bold text-gray-900">{totalProducts}</p>
                </div>
                <Package className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Kam Qolgan Mahsulotlar</p>
                  <p className="text-2xl font-bold text-red-600">{lowStockProducts.length}</p>
                </div>
                <AlertTriangle className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">O'qilmagan Bildirishnomalar</p>
                  <p className="text-2xl font-bold text-orange-600">{unreadNotifications}</p>
                </div>
                <Activity className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Row - Only for admin and menejer */}
      {user?.role.name !== 'oshpaz' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Stock Status Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Mahsulotlar Holati</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={stockStatusData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {stockStatusData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center space-x-4 mt-4">
                  {stockStatusData.map((entry, index) => (
                    <div key={index} className="flex items-center">
                      <div 
                        className="w-3 h-3 rounded-full mr-2" 
                        style={{ backgroundColor: entry.color }}
                      ></div>
                      <span className="text-sm text-gray-600">{entry.name}: {entry.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Ingredient Consumption Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Ingredientlar Iste'moli (So'nggi 30 kun)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ingredientConsumption.slice(0, 10)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="product_name" 
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        fontSize={12}
                      />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="total_consumed" fill="#3B82F6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Delivery Trends Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Yetkazib Berish Trendlari (So'nggi 30 kun)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={deliveryTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="delivery_date" />
                    <YAxis />
                    <Tooltip />
                    <Line 
                      type="monotone" 
                      dataKey="total_delivered" 
                      stroke="#10B981" 
                      strokeWidth={2}
                      dot={{ fill: '#10B981' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Tizim Holati - Only for admin and menejer */}
          <Card>
            <CardHeader>
              <CardTitle>Tizim Holati</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Umumiy mahsulotlar</span>
                  <span className="font-medium">{totalProducts}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Kam qolgan mahsulotlar</span>
                  <span className="font-medium text-red-600">{lowStockProducts.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">O'qilmagan bildirishnomalar</span>
                  <span className="font-medium">{unreadNotifications}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Low Stock Alert - Only for admin and menejer */}
          {lowStockProducts.length > 0 && (
            <Card className="border-red-200 bg-red-50">
              <CardHeader>
                <CardTitle className="text-red-800 flex items-center">
                  <AlertTriangle className="h-5 w-5 mr-2" />
                  Kam Qolgan Mahsulotlar Ogohlantirishi
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {lowStockProducts.map((product: any) => {
                    const currentQuantity = product.current_quantity !== undefined ? product.current_quantity : product.quantity || 0;
                    const minQuantity = product.min_quantity || product.min_stock_level || 0;
                    const unitName = product.unit?.short_name || product.unit || 'dona';
                    
                    return (
                      <div key={product.id} className="bg-white p-3 rounded border border-red-200">
                        <p className="font-medium text-gray-900">{product.name}</p>
                        <p className="text-sm text-red-600">
                          Qolgan: {currentQuantity} {unitName}
                        </p>
                        <p className="text-xs text-gray-500">
                          Minimal chegara: {minQuantity} {unitName}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default DashboardPage;
