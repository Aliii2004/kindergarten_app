import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Plus, Search, ChefHat, Eye, Users, Package, Edit, Trash2 } from 'lucide-react';
import { mealService } from '@/services/mealService';
import { productService } from '@/services/productService';
import { Meal } from '@/types/meals';

const MealsPage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showActiveOnly, setShowActiveOnly] = useState(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const [selectedMealId, setSelectedMealId] = useState<number | null>(null);
  const [editingMeal, setEditingMeal] = useState<Meal | null>(null);
  const [ingredients, setIngredients] = useState([{ product_id: '', quantity_per_portion: '', unit_id: '' }]);
  const [editIngredients, setEditIngredients] = useState([{ product_id: '', quantity_per_portion: '', unit_id: '' }]);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch meals
  const { data: meals = [], isLoading, error } = useQuery({
    queryKey: ['meals', searchQuery, showActiveOnly],
    queryFn: async () => {
      return await mealService.getMeals({
        name_filter: searchQuery || undefined,
        active_only: showActiveOnly || undefined,
        limit: 100
      });
    }
  });

  // Fetch products for ingredients
  const { data: products = [] } = useQuery({
    queryKey: ['products-for-meals'],
    queryFn: async () => {
      return await productService.getProducts({ limit: 200 });
    }
  });

  // Fetch units
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn: async () => {
      return await productService.getUnits(0, 100);
    }
  });

  // Fetch individual meal details
  const { data: mealDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['meal-details', selectedMealId],
    queryFn: async () => {
      if (!selectedMealId) return null;
      return await mealService.getMeal(selectedMealId);
    },
    enabled: !!selectedMealId && isDetailsDialogOpen
  });

  // Create meal mutation
  const createMealMutation = useMutation({
    mutationFn: async (data: any) => {
      return await mealService.createMeal(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meals'] });
      setIsCreateDialogOpen(false);
      setIngredients([{ product_id: '', quantity_per_portion: '', unit_id: '' }]);
      toast({
        title: "Muvaffaqiyat",
        description: "Ovqat muvaffaqiyatli yaratildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Ovqat yaratishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Update meal mutation
  const updateMealMutation = useMutation({
    mutationFn: async (data: { id: number; mealData: any }) => {
      return await mealService.updateMeal(data.id, data.mealData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meals'] });
      setIsEditDialogOpen(false);
      setEditingMeal(null);
      setEditIngredients([{ product_id: '', quantity_per_portion: '', unit_id: '' }]);
      toast({
        title: "Muvaffaqiyat",
        description: "Ovqat muvaffaqiyatli yangilandi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Ovqatni yangilashda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Delete meal mutation
  const deleteMealMutation = useMutation({
    mutationFn: async (mealId: number) => {
      return await mealService.deleteMeal(mealId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['meals'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Ovqat muvaffaqiyatli o'chirildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Ovqatni o'chirishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  const handleViewDetails = (mealId: number) => {
    setSelectedMealId(mealId);
    setIsDetailsDialogOpen(true);
  };

  const handleEditMeal = (meal: Meal) => {
    setEditingMeal(meal);
    // Set ingredients from meal data
    if (meal.ingredients && meal.ingredients.length > 0) {
      setEditIngredients(meal.ingredients.map(ing => ({
        product_id: ing.product_id?.toString() || '',
        quantity_per_portion: ing.quantity_per_portion?.toString() || '',
        unit_id: ing.unit_id?.toString() || ''
      })));
    } else {
      setEditIngredients([{ product_id: '', quantity_per_portion: '', unit_id: '' }]);
    }
    setIsEditDialogOpen(true);
  };

  const handleDeleteMeal = (mealId: number) => {
    if (confirm('Bu ovqatni o\'chirishni tasdiqlaysizmi?')) {
      deleteMealMutation.mutate(mealId);
    }
  };

  const handleCreateMeal = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    const validIngredients = ingredients.filter(ing => 
      ing.product_id && ing.quantity_per_portion && ing.unit_id
    ).map(ing => ({
      product_id: parseInt(ing.product_id),
      quantity_per_portion: parseFloat(ing.quantity_per_portion),
      unit_id: parseInt(ing.unit_id)
    }));

    const data = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      is_active: formData.get('is_active') === 'on',
      ingredients: validIngredients
    };
    
    createMealMutation.mutate(data);
  };

  const handleUpdateMeal = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingMeal) return;

    const formData = new FormData(e.currentTarget);
    
    const validIngredients = editIngredients.filter(ing => 
      ing.product_id && ing.quantity_per_portion && ing.unit_id
    ).map(ing => ({
      product_id: parseInt(ing.product_id),
      quantity_per_portion: parseFloat(ing.quantity_per_portion),
      unit_id: parseInt(ing.unit_id)
    }));

    const mealData = {
      name: formData.get('name') as string,
      description: formData.get('description') as string,
      is_active: formData.get('is_active') === 'on',
      ingredients: validIngredients
    };
    
    updateMealMutation.mutate({ id: editingMeal.id, mealData });
  };

  const addIngredient = () => {
    setIngredients([...ingredients, { product_id: '', quantity_per_portion: '', unit_id: '' }]);
  };

  const removeIngredient = (index: number) => {
    setIngredients(ingredients.filter((_, i) => i !== index));
  };

  const updateIngredient = (index: number, field: string, value: string) => {
    const updated = [...ingredients];
    updated[index] = { ...updated[index], [field]: value };
    setIngredients(updated);
  };

  const addEditIngredient = () => {
    setEditIngredients([...editIngredients, { product_id: '', quantity_per_portion: '', unit_id: '' }]);
  };

  const removeEditIngredient = (index: number) => {
    setEditIngredients(editIngredients.filter((_, i) => i !== index));
  };

  const updateEditIngredient = (index: number, field: string, value: string) => {
    const updated = [...editIngredients];
    updated[index] = { ...updated[index], [field]: value };
    setEditIngredients(updated);
  };

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('uz-UZ');
    } catch (error) {
      return 'Noma\'lum sana';
    }
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center">Yuklanmoqda...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center text-red-600">Ovqatlarni yuklashda xatolik yuz berdi</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Ovqatlar</h1>
          <p className="text-gray-600">Ovqat retseptlarini boshqarish</p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Yangi ovqat
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Yangi ovqat yaratish</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateMeal} className="space-y-4">
              <div>
                <Label htmlFor="name">Nomi</Label>
                <Input name="name" required />
              </div>
              <div>
                <Label htmlFor="description">Tavsif</Label>
                <Textarea name="description" />
              </div>
              <div className="flex items-center space-x-2">
                <Switch name="is_active" id="is_active" defaultChecked />
                <Label htmlFor="is_active">Faol</Label>
              </div>
              
              <div>
                <Label>Ingredientlar</Label>
                <div className="space-y-3">
                  {ingredients.map((ingredient, index) => (
                    <div key={index} className="flex gap-2 items-end">
                      <div className="flex-1">
                        <Select 
                          value={ingredient.product_id} 
                          onValueChange={(value) => updateIngredient(index, 'product_id', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Mahsulot" />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((product: any) => (
                              <SelectItem key={product.id} value={product.id.toString()}>
                                {product.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="w-24">
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Miqdor"
                          value={ingredient.quantity_per_portion}
                          onChange={(e) => updateIngredient(index, 'quantity_per_portion', e.target.value)}
                        />
                      </div>
                      <div className="w-32">
                        <Select 
                          value={ingredient.unit_id} 
                          onValueChange={(value) => updateIngredient(index, 'unit_id', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Birlik" />
                          </SelectTrigger>
                          <SelectContent>
                            {units.map((unit: any) => (
                              <SelectItem key={unit.id} value={unit.id.toString()}>
                                {unit.short_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeIngredient(index)}
                        disabled={ingredients.length === 1}
                      >
                        O'chirish
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="outline" onClick={addIngredient}>
                    Ingredient qo'shish
                  </Button>
                </div>
              </div>
              
              <Button type="submit" disabled={createMealMutation.isPending}>
                {createMealMutation.isPending ? 'Yaratilmoqda...' : 'Yaratish'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Ovqat qidirish..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                checked={showActiveOnly}
                onCheckedChange={setShowActiveOnly}
                id="active-only"
              />
              <Label htmlFor="active-only">Faqat faollar</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Meals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {meals.map((meal: Meal) => (
          <Card key={meal.id} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <CardTitle className="text-lg">{meal.name}</CardTitle>
                <div className="flex items-center gap-2">
                  <ChefHat className="h-5 w-5 text-gray-400" />
                  <Badge variant={meal.is_active ? "default" : "secondary"}>
                    {meal.is_active ? "Faol" : "Nofaol"}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-gray-600 line-clamp-2">{meal.description}</p>
              <div className="flex justify-between text-sm">
                <span>Ingredientlar:</span>
                <span>{meal.ingredients?.length || 0} ta</span>
              </div>
              {meal.possible_portions !== undefined && (
                <div className="flex justify-between text-sm">
                  <span>Mumkin porsiya:</span>
                  <Badge variant="outline">
                    <Users className="h-3 w-3 mr-1" />
                    {meal.possible_portions}
                  </Badge>
                </div>
              )}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleViewDetails(meal.id)}
                  className="flex-1"
                >
                  <Eye className="h-3 w-3 mr-1" />
                  Ko'rish
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleEditMeal(meal)}
                >
                  <Edit className="h-3 w-3" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteMeal(meal.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Meal Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ovqatni tahrirlash</DialogTitle>
          </DialogHeader>
          {editingMeal && (
            <form onSubmit={handleUpdateMeal} className="space-y-4">
              <div>
                <Label htmlFor="edit-name">Nomi</Label>
                <Input 
                  id="edit-name"
                  name="name" 
                  required 
                  defaultValue={editingMeal.name}
                />
              </div>
              <div>
                <Label htmlFor="edit-description">Tavsif</Label>
                <Textarea 
                  id="edit-description"
                  name="description" 
                />
              </div>
              <div className="flex items-center space-x-2">
                <Switch 
                  name="is_active" 
                  id="edit-is_active" 
                  defaultChecked={editingMeal.is_active}
                />
                <Label htmlFor="edit-is_active">Faol</Label>
              </div>
              
              <div>
                <Label>Ingredientlar</Label>
                <div className="space-y-3">
                  {editIngredients.map((ingredient, index) => (
                    <div key={index} className="flex gap-2 items-end">
                      <div className="flex-1">
                        <Select 
                          value={ingredient.product_id} 
                          onValueChange={(value) => updateEditIngredient(index, 'product_id', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Mahsulot" />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((product: any) => (
                              <SelectItem key={product.id} value={product.id.toString()}>
                                {product.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="w-24">
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Miqdor"
                          value={ingredient.quantity_per_portion}
                          onChange={(e) => updateEditIngredient(index, 'quantity_per_portion', e.target.value)}
                        />
                      </div>
                      <div className="w-32">
                        <Select 
                          value={ingredient.unit_id} 
                          onValueChange={(value) => updateEditIngredient(index, 'unit_id', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Birlik" />
                          </SelectTrigger>
                          <SelectContent>
                            {units.map((unit: any) => (
                              <SelectItem key={unit.id} value={unit.id.toString()}>
                                {unit.short_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => removeEditIngredient(index)}
                        disabled={editIngredients.length === 1}
                      >
                        O'chirish
                      </Button>
                    </div>
                  ))}
                  <Button type="button" variant="outline" onClick={addEditIngredient}>
                    Ingredient qo'shish
                  </Button>
                </div>
              </div>
              
              <Button type="submit" disabled={updateMealMutation.isPending}>
                {updateMealMutation.isPending ? 'Tahrirlanmoqda...' : 'Tahrirlash'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Meal Details Dialog */}
      <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ovqat tafsilotlari</DialogTitle>
          </DialogHeader>
          {detailsLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : mealDetails ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Nomi</Label>
                  <p className="font-medium">{mealDetails.name}</p>
                </div>
                <div>
                  <Label>Holat</Label>
                  <Badge variant={mealDetails.is_active ? "default" : "secondary"}>
                    {mealDetails.is_active ? "Faol" : "Nofaol"}
                  </Badge>
                </div>
                <div className="col-span-2">
                  <Label>Tavsif</Label>
                  <p className="text-gray-600">{mealDetails.description}</p>
                </div>
                {mealDetails.possible_portions !== undefined && (
                  <div>
                    <Label>Mumkin porsiyalar</Label>
                    <p className="font-medium">{mealDetails.possible_portions}</p>
                  </div>
                )}
                <div>
                  <Label>Yaratilgan</Label>
                  <p>{formatDate(mealDetails.created_at)}</p>
                </div>
                {mealDetails.created_by_user && (
                  <div>
                    <Label>Yaratgan oshpaz</Label>
                    <p className="font-medium">{mealDetails.created_by_user.full_name}</p>
                  </div>
                )}
              </div>

              {mealDetails.ingredients && mealDetails.ingredients.length > 0 && (
                <div>
                  <Label className="text-lg">Ingredientlar</Label>
                  <div className="mt-2 space-y-2">
                    {mealDetails.ingredients.map((ingredient: any) => (
                      <div key={ingredient.id} className="flex justify-between items-center p-3 border rounded">
                        <div className="flex items-center">
                          <Package className="h-4 w-4 mr-2 text-gray-400" />
                          <span className="font-medium">{ingredient.product?.name || 'Noma\'lum mahsulot'}</span>
                        </div>
                        <span className="text-sm text-gray-600">
                          {ingredient.quantity_per_portion} {ingredient.unit?.short_name || 'dona'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Ovqat tafsilotlari yuklanmadi
            </div>
          )}
        </DialogContent>
      </Dialog>

      {meals.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <ChefHat className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ovqatlar topilmadi</h3>
            <p className="text-gray-600">
              {searchQuery 
                ? "Qidiruv shartlariga mos ovqatlar topilmadi"
                : "Hali ovqatlar qo'shilmagan"
              }
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default MealsPage;
