
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { FileText, Download, Calendar, TrendingUp, Package, Eye, RefreshCw, Plus } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { reportService } from '@/services/reportService';

const ReportsPage = () => {
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [isReportDetailsOpen, setIsReportDetailsOpen] = useState(false);
  
  // Date range for charts - default to last 30 days
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });

  const { toast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Generate monthly report mutation
  const generateReportMutation = useMutation({
    mutationFn: async () => {
      console.log('Generating report for:', selectedYear, selectedMonth);
      return await reportService.generateMonthlyReport(selectedYear, selectedMonth);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monthly-reports'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Oylik hisobot muvaffaqiyatli yaratildi"
      });
    },
    onError: (error: any) => {
      console.error('Report generation error:', error);
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Hisobot yaratishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Fetch monthly reports with increased limit
  const { data: monthlyReports = [], isLoading: reportsLoading, error: reportsError } = useQuery({
    queryKey: ['monthly-reports'],
    queryFn: async () => {
      try {
        console.log('Fetching monthly reports...');
        const result = await reportService.getMonthlyReports(0, 500); // Increased limit to 500
        console.log('Monthly reports result:', result);
        return Array.isArray(result) ? result : [];
      } catch (error) {
        console.error('Error fetching monthly reports:', error);
        return [];
      }
    },
    retry: 1
  });

  // Fetch detailed monthly report
  const { data: reportDetails, isLoading: reportDetailsLoading } = useQuery({
    queryKey: ['monthly-report-details', selectedReportId],
    queryFn: async () => {
      if (!selectedReportId) return null;
      console.log('Fetching report details for ID:', selectedReportId);
      return await reportService.getMonthlyReport(selectedReportId);
    },
    enabled: !!selectedReportId && isReportDetailsOpen
  });

  // Fetch ingredient consumption data
  const { data: ingredientData = [], isLoading: ingredientLoading, error: ingredientError } = useQuery({
    queryKey: ['ingredient-consumption', startDate, endDate],
    queryFn: async () => {
      console.log('Fetching ingredient consumption data...', startDate, endDate);
      const result = await reportService.getIngredientConsumptionData(startDate, endDate);
      return Array.isArray(result) ? result : [];
    },
    enabled: !!(startDate && endDate)
  });

  // Fetch delivery trends data
  const { data: deliveryTrends = [], isLoading: trendsLoading, error: trendsError } = useQuery({
    queryKey: ['delivery-trends', startDate, endDate],
    queryFn: async () => {
      console.log('Fetching delivery trends data...', startDate, endDate);
      const result = await reportService.getProductDeliveryTrends(startDate, endDate);
      return Array.isArray(result) ? result : [];
    },
    enabled: !!(startDate && endDate)
  });

  const months = [
    { value: 1, label: 'Yanvar' },
    { value: 2, label: 'Fevral' },
    { value: 3, label: 'Mart' },
    { value: 4, label: 'Aprel' },
    { value: 5, label: 'May' },
    { value: 6, label: 'Iyun' },
    { value: 7, label: 'Iyul' },
    { value: 8, label: 'Avgust' },
    { value: 9, label: 'Sentabr' },
    { value: 10, label: 'Oktabr' },
    { value: 11, label: 'Noyabr' },
    { value: 12, label: 'Dekabr' }
  ];

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

  const handleViewReportDetails = (reportId: number) => {
    setSelectedReportId(reportId);
    setIsReportDetailsOpen(true);
  };

  const handleRefreshCharts = () => {
    queryClient.invalidateQueries({ queryKey: ['ingredient-consumption'] });
    queryClient.invalidateQueries({ queryKey: ['delivery-trends'] });
    toast({
      title: "Muvaffaqiyat",
      description: "Grafiklar yangilandi"
    });
  };

  const handleRefreshReports = () => {
    queryClient.invalidateQueries({ queryKey: ['monthly-reports'] });
    toast({
      title: "Muvaffaqiyat",
      description: "Hisobotlar ro'yxati yangilandi"
    });
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

  const getMonthName = (month: number) => {
    const monthNames = months.find(m => m.value === month);
    return monthNames ? monthNames.label : month.toString();
  };

  // Helper function to get meal name from ingredient details
  const getMealNameFromIngredients = (mealId: number, ingredientDetails: any[]) => {
    const ingredient = ingredientDetails.find((ing: any) => ing.meal_id === mealId);
    return ingredient?.meal_for_ingredient_detail?.name || 'Noma\'lum ovqat';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Hisobotlar</h1>
          <p className="text-gray-600">Tizim hisobotlari va analitika</p>
        </div>
      </div>

      {/* Monthly Reports List */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center">
              <FileText className="h-5 w-5 mr-2" />
              Yaratilgan Oylik Hisobotlar
            </CardTitle>
            <div className="flex gap-2">
              <Button 
                onClick={handleRefreshReports}
                variant="outline"
                size="sm"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Yangilash
              </Button>
              {user?.role.name === 'admin' && (
                <Button 
                  onClick={() => generateReportMutation.mutate()}
                  disabled={generateReportMutation.isPending}
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  {generateReportMutation.isPending ? 'Yaratilmoqda...' : 'Yangi Hisobot'}
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {reportsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Hisobotlar yuklanmoqda...</p>
            </div>
          ) : reportsError ? (
            <div className="text-center py-8 text-amber-600">
              <p>Hisobotlar hozircha mavjud emas</p>
              <p className="text-sm text-gray-500 mt-1">Backend hisobotlar modulini sozlang</p>
            </div>
          ) : monthlyReports.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="h-12 w-12 mx-auto text-gray-300 mb-4" />
              <p className="text-lg font-medium mb-2">Hali hisobotlar yaratilmagan</p>
              <p className="text-sm">Birinchi hisobotni yaratish uchun yuqoridagi tugmani bosing</p>
            </div>
          ) : (
            <div className="space-y-3">
              {monthlyReports.map((report: any) => (
                <div key={report.id} className="flex justify-between items-center p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <div className="bg-blue-100 p-2 rounded">
                        <FileText className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-lg">
                          {getMonthName(new Date(report.report_month).getMonth() + 1)} {new Date(report.report_month).getFullYear()} - Oylik Hisobot
                        </h3>
                        <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                          <span>Yaratilgan: {formatDate(report.generated_at)}</span>
                          <span>Yaratgan: {report.generated_by_user?.full_name || 'Tizim'}</span>
                          <span className={`px-2 py-1 rounded text-xs ${
                            report.is_overall_suspicious 
                              ? 'bg-red-100 text-red-700' 
                              : 'bg-green-100 text-green-700'
                          }`}>
                            {report.is_overall_suspicious ? 'Shubhali' : 'Normal'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500 mt-1">
                          Umumiy berilgan porsiyalar: {report.total_portions_served_overall || 0}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={() => handleViewReportDetails(report.id)}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Ko'rish
                    </Button>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-1" />
                      Yuklab olish
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Monthly Report Generation - Admin Only */}
      {user?.role.name === 'admin' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Plus className="h-5 w-5 mr-2" />
              Yangi Oylik Hisobot Yaratish
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 items-end">
              <div>
                <Label>Yil</Label>
                <Select value={selectedYear.toString()} onValueChange={(value) => setSelectedYear(parseInt(value))}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {years.map(year => (
                      <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Oy</Label>
                <Select value={selectedMonth.toString()} onValueChange={(value) => setSelectedMonth(parseInt(value))}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {months.map(month => (
                      <SelectItem key={month.value} value={month.value.toString()}>{month.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button 
                onClick={() => generateReportMutation.mutate()}
                disabled={generateReportMutation.isPending}
              >
                <Plus className="h-4 w-4 mr-2" />
                {generateReportMutation.isPending ? 'Yaratilmoqda...' : 'Hisobot Yaratish'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Date Range Filter for Charts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Calendar className="h-5 w-5 mr-2" />
            Grafik Ma'lumotlari Uchun Sana Diapazoni
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 items-end">
            <div>
              <Label>Boshlanish sanasi</Label>
              <Input 
                type="date" 
                value={startDate} 
                onChange={(e) => setStartDate(e.target.value)}
                className="w-40"
              />
            </div>
            <div>
              <Label>Tugash sanasi</Label>
              <Input 
                type="date" 
                value={endDate} 
                onChange={(e) => setEndDate(e.target.value)}
                className="w-40"
              />
            </div>
            <Button 
              onClick={handleRefreshCharts}
              variant="outline"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Yangilash
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Report Details Dialog */}
      <Dialog open={isReportDetailsOpen} onOpenChange={setIsReportDetailsOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Oylik Hisobot Tafsilotlari</DialogTitle>
          </DialogHeader>
          {reportDetailsLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Yuklanmoqda...</p>
            </div>
          ) : reportDetails ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="font-semibold mb-2">Umumiy Ma'lumotlar</h3>
                  <p>Hisobot oyi: {formatDate(reportDetails.report_month)}</p>
                  <p>Jami berilgan porsiyalar: {reportDetails.total_portions_served_overall || 0}</p>
                  <p>Shubhali holat: {reportDetails.is_overall_suspicious ? 'Ha' : 'Yo\'q'}</p>
                </div>
                <div>
                  <h3 className="font-semibold mb-2">Yaratilgan</h3>
                  <p>{formatDate(reportDetails.generated_at)}</p>
                  <p>Yaratgan: {reportDetails.generated_by_user?.full_name || 'Tizim'}</p>
                </div>
              </div>

              {reportDetails.meal_performance_summaries && reportDetails.meal_performance_summaries.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Ovqatlar Samaradorligi</h3>
                  <div className="space-y-2">
                    {reportDetails.meal_performance_summaries.map((meal: any) => {
                      const mealName = getMealNameFromIngredients(meal.meal_id, reportDetails.all_ingredient_usage_details || []);
                      
                      return (
                        <div key={meal.id} className="p-3 border rounded">
                          <p className="font-medium">{mealName}</p>
                          <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
                            <span>Berilgan: {meal.portions_served_this_meal}</span>
                            <span>Mumkin edi: {meal.possible_portions_at_report_time}</span>
                            <span className={meal.is_suspicious ? 'text-red-600' : 'text-green-600'}>
                              {meal.is_suspicious ? 'Shubhali' : 'Normal'}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {reportDetails.all_ingredient_usage_details && reportDetails.all_ingredient_usage_details.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Ingredientlar Iste'moli</h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {reportDetails.all_ingredient_usage_details.map((ingredient: any) => (
                      <div key={ingredient.id} className="p-2 border rounded text-sm">
                        <span className="font-medium">{ingredient.product_for_ingredient_detail?.name}</span>
                        <span className="ml-2 text-gray-600">
                          {ingredient.total_quantity_used} ishlatilgan
                        </span>
                        <span className="ml-2 text-blue-600">
                          ({ingredient.meal_for_ingredient_detail?.name})
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reportDetails.product_balance_summaries && reportDetails.product_balance_summaries.length > 0 && (
                <div>
                  <h3 className="font-semibold mb-2">Mahsulotlar Balansi</h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {reportDetails.product_balance_summaries.map((balance: any) => (
                      <div key={balance.id} className={`p-3 border rounded ${balance.is_balance_suspicious ? 'border-red-200 bg-red-50' : 'border-gray-200'}`}>
                        <p className="font-medium">{balance.product_in_balance?.name}</p>
                        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mt-2">
                          <div>
                            <p>Boshlang'ich: {balance.initial_stock}</p>
                            <p>Olingan: {balance.total_received}</p>
                            <p>Jami mavjud: {balance.total_available}</p>
                          </div>
                          <div>
                            <p>Hisoblangan iste'mol: {balance.calculated_consumption.toFixed(2)}</p>
                            <p>Haqiqiy iste'mol: {balance.actual_consumption}</p>
                            <p className={`font-medium ${balance.is_balance_suspicious ? 'text-red-600' : 'text-green-600'}`}>
                              Farq: {balance.discrepancy.toFixed(2)} ({balance.discrepancy_percentage}%)
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Hisobot tafsilotlari yuklanmadi
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Ingredient Consumption Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Package className="h-5 w-5 mr-2" />
            Ingredientlar Iste'moli ({startDate} dan {endDate} gacha)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {ingredientLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : ingredientError ? (
            <div className="text-center py-8 text-red-600">
              Ma'lumotlarni yuklashda xatolik: {ingredientError.message}
            </div>
          ) : ingredientData.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Tanlangan sana oralig'ida ingredientlar iste'moli ma'lumotlari topilmadi
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={ingredientData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="product_name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_consumed" fill="#16a34a" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Delivery Trends Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <TrendingUp className="h-5 w-5 mr-2" />
            Mahsulot Yetkazib Berish Trendlari ({startDate} dan {endDate} gacha)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {trendsLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : trendsError ? (
            <div className="text-center py-8 text-red-600">
              Ma'lumotlarni yuklashda xatolik: {trendsError.message}
            </div>
          ) : deliveryTrends.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Tanlangan sana oralig'ida yetkazib berish ma'lumotlari topilmadi
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={deliveryTrends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="delivery_date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="total_delivered" stroke="#16a34a" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ReportsPage;
