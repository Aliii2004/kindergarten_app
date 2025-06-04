import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { ChefHat, Plus, Clock, Users, RefreshCw } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { mealService, servingService } from '@/services/mealService';
import { useWebSocket } from '@/hooks/useWebSocket';

const ServingsPage = () => {
  const [selectedMealId, setSelectedMealId] = useState<string>('');
  const [portions, setPortions] = useState<number>(1);
  const [notes, setNotes] = useState('');
  const [isServeDialogOpen, setIsServeDialogOpen] = useState(false);

  const { toast } = useToast();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { messages } = useWebSocket();

  // Listen for WebSocket messages to update available meals in real-time
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.type === 'meal_served' || lastMessage?.type === 'stock_updated') {
      // Invalidate queries to refresh available meals immediately
      queryClient.invalidateQueries({ queryKey: ['available-meals'] });
      queryClient.invalidateQueries({ queryKey: ['servings'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    }
  }, [messages, queryClient]);

  // Fetch available meals for serving
  const { data: availableMeals = [], isLoading: mealsLoading } = useQuery({
    queryKey: ['available-meals'],
    queryFn: () => mealService.getAvailableMeals()
  });

  // Fetch servings history - only for admin and menejer
  const { data: servings = [], isLoading: servingsLoading } = useQuery({
    queryKey: ['servings'],
    queryFn: () => servingService.getServings({ limit: 50 }),
    enabled: user?.role.name !== 'oshpaz'
  });

  // Create serving mutation
  const createServingMutation = useMutation({
    mutationFn: async (servingData: { meal_id: number; portions_served: number; notes?: string }) => {
      return await servingService.createServing(servingData);
    },
    onSuccess: () => {
      // Immediately invalidate all related queries for instant update
      queryClient.invalidateQueries({ queryKey: ['available-meals'] });
      queryClient.invalidateQueries({ queryKey: ['servings'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['meals'] });
      
      // Force refetch available meals immediately
      queryClient.refetchQueries({ queryKey: ['available-meals'] });
      
      // Only recalculate portions for admin and menejer (not for oshpaz)
      if (user?.role.name !== 'oshpaz') {
        mealService.recalculatePortions().then(() => {
          queryClient.invalidateQueries({ queryKey: ['available-meals'] });
          queryClient.refetchQueries({ queryKey: ['available-meals'] });
        });
      }

      setIsServeDialogOpen(false);
      setSelectedMealId('');
      setPortions(1);
      setNotes('');
      
      toast({
        title: "Muvaffaqiyat",
        description: "Ovqat muvaffaqiyatli berildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Ovqat berishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Recalculate portions manually - only for admin and menejer
  const recalculateMutation = useMutation({
    mutationFn: () => mealService.recalculatePortions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['available-meals'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Mumkin bo'lgan porsiyalar qayta hisoblab chiqildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: "Qayta hisoblashda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  const handleServeFood = () => {
    if (!selectedMealId || portions < 1) {
      toast({
        title: "Xatolik",
        description: "Ovqat va porsiya miqdorini to'g'ri tanlang",
        variant: "destructive"
      });
      return;
    }

    createServingMutation.mutate({
      meal_id: parseInt(selectedMealId),
      portions_served: portions,
      notes: notes || undefined
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

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Ovqat Berish</h1>
          <p className="text-gray-600">Ovqatlarni bolalarga berish</p>
        </div>
        <div className="flex gap-2">
          {/* Qayta hisoblash tugmasi faqat admin va menejer uchun */}
          {user?.role.name !== 'oshpaz' && (
            <Button 
              onClick={() => recalculateMutation.mutate()}
              disabled={recalculateMutation.isPending}
              variant="outline"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Qayta Hisoblash
            </Button>
          )}
          <Dialog open={isServeDialogOpen} onOpenChange={setIsServeDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Ovqat Berish
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Ovqat Berish</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Ovqat</Label>
                  <Select value={selectedMealId} onValueChange={setSelectedMealId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Ovqat tanlang" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableMeals.map((meal: any) => (
                        <SelectItem key={meal.meal_id} value={meal.meal_id.toString()}>
                          {meal.meal_name} (Mumkin: {meal.possible_portions} porsiya)
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Porsiya miqdori</Label>
                  <Input
                    type="number"
                    min="1"
                    value={portions}
                    onChange={(e) => setPortions(parseInt(e.target.value) || 1)}
                  />
                </div>
                <div>
                  <Label>Izoh (ixtiyoriy)</Label>
                  <Textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Qo'shimcha izoh..."
                  />
                </div>
                <Button 
                  onClick={handleServeFood}
                  disabled={createServingMutation.isPending}
                  className="w-full"
                >
                  {createServingMutation.isPending ? 'Berilmoqda...' : 'Ovqat Berish'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Available Meals */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <ChefHat className="h-5 w-5 mr-2" />
            Berishga Tayyor Ovqatlar
          </CardTitle>
        </CardHeader>
        <CardContent>
          {mealsLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : availableMeals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              Hozircha berishga tayyor ovqatlar mavjud emas
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {availableMeals.map((meal: any) => (
                <div key={meal.meal_id} className="border rounded-lg p-4">
                  <h3 className="font-semibold text-lg">{meal.meal_name}</h3>
                  <p className="text-sm text-gray-600 mb-2">
                    Mumkin bo'lgan porsiyalar: <span className="font-medium text-green-600">{meal.possible_portions}</span>
                  </p>
                  <p className="text-xs text-gray-500">
                    Cheklovchi ingredient: {meal.limiting_ingredient_name}
                  </p>
                  <Button 
                    size="sm" 
                    className="mt-3 w-full"
                    onClick={() => {
                      setSelectedMealId(meal.meal_id.toString());
                      setIsServeDialogOpen(true);
                    }}
                    disabled={meal.possible_portions === 0}
                  >
                    <Users className="h-4 w-4 mr-2" />
                    Berish
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Servings History - Only for admin and menejer */}
      {user?.role.name !== 'oshpaz' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Clock className="h-5 w-5 mr-2" />
              Ovqat Berish Tarixi
            </CardTitle>
          </CardHeader>
          <CardContent>
            {servingsLoading ? (
              <div className="text-center py-8">Yuklanmoqda...</div>
            ) : servings.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Hali ovqat berish tarixi mavjud emas
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ovqat</TableHead>
                    <TableHead>Porsiya</TableHead>
                    <TableHead>Bergan</TableHead>
                    <TableHead>Sana</TableHead>
                    <TableHead>Izoh</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {servings.map((serving: any) => (
                    <TableRow key={serving.id}>
                      <TableCell>{serving.meal?.name || 'Noma\'lum ovqat'}</TableCell>
                      <TableCell>{serving.portions_served}</TableCell>
                      <TableCell>{serving.served_by_user?.full_name || 'Noma\'lum'}</TableCell>
                      <TableCell>{formatDate(serving.served_at)}</TableCell>
                      <TableCell>{serving.notes || '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ServingsPage;
