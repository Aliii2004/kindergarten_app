
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Plus, Search, Package, AlertTriangle, Eye, Truck, Edit, Trash2 } from 'lucide-react';
import { productService } from '@/services/productService';
import { Product, Unit } from '@/types/products';

const ProductsPage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showLowStockOnly, setShowLowStockOnly] = useState(false);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeliveryDialogOpen, setIsDeliveryDialogOpen] = useState(false);
  const [isDetailsDialogOpen, setIsDetailsDialogOpen] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch products with correct limit
  const { data: products = [], isLoading, error } = useQuery({
    queryKey: ['products', searchQuery, showLowStockOnly],
    queryFn: async () => {
      return await productService.getProducts({
        name_filter: searchQuery || undefined,
        low_stock_only: showLowStockOnly || undefined,
        limit: 200 // Backend maksimal limit
      });
    }
  });

  // Fetch units for creating products
  const { data: units = [] } = useQuery({
    queryKey: ['units'],
    queryFn: async () => {
      return await productService.getUnits(0, 100);
    }
  });

  // Fetch individual product details
  const { data: productDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['product-details', selectedProductId],
    queryFn: async () => {
      if (!selectedProductId) return null;
      return await productService.getProduct(selectedProductId);
    },
    enabled: !!selectedProductId && isDetailsDialogOpen
  });

  // Create product mutation
  const createProductMutation = useMutation({
    mutationFn: async (data: { name: string; unit_id: number; min_quantity: number }) => {
      return await productService.createProduct(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setIsCreateDialogOpen(false);
      toast({
        title: "Muvaffaqiyat",
        description: "Mahsulot muvaffaqiyatli yaratildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Mahsulot yaratishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Update product mutation
  const updateProductMutation = useMutation({
    mutationFn: async (data: { id: number; name: string; unit_id: number; min_quantity: number }) => {
      const { id, ...updateData } = data;
      return await productService.updateProduct(id, updateData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setIsEditDialogOpen(false);
      setEditingProduct(null);
      toast({
        title: "Muvaffaqiyat",
        description: "Mahsulot muvaffaqiyatli yangilandi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Mahsulotni yangilashda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Delete product mutation
  const deleteProductMutation = useMutation({
    mutationFn: async (productId: number) => {
      return await productService.deleteProduct(productId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Mahsulot muvaffaqiyatli o'chirildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Mahsulotni o'chirishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Create delivery mutation
  const createDeliveryMutation = useMutation({
    mutationFn: async (data: { product_id: number; quantity: number; delivery_date: string; supplier: string; price: number }) => {
      return await productService.createDelivery(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      setIsDeliveryDialogOpen(false);
      toast({
        title: "Muvaffaqiyat",
        description: "Yetkazib berish muvaffaqiyatli qo'shildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Yetkazib berish qo'shishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  const handleViewDetails = (productId: number) => {
    setSelectedProductId(productId);
    setIsDetailsDialogOpen(true);
  };

  const handleEditProduct = (product: Product) => {
    setEditingProduct(product);
    setIsEditDialogOpen(true);
  };

  const handleDeleteProduct = (productId: number) => {
    if (confirm('Bu mahsulotni o\'chirishni tasdiqlaysizmi?')) {
      deleteProductMutation.mutate(productId);
    }
  };

  const handleCreateProduct = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get('name') as string,
      unit_id: parseInt(formData.get('unit_id') as string),
      min_quantity: parseInt(formData.get('min_quantity') as string)
    };
    createProductMutation.mutate(data);
  };

  const handleUpdateProduct = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingProduct) return;
    
    const formData = new FormData(e.currentTarget);
    const data = {
      id: editingProduct.id,
      name: formData.get('name') as string,
      unit_id: parseInt(formData.get('unit_id') as string),
      min_quantity: parseInt(formData.get('min_quantity') as string)
    };
    updateProductMutation.mutate(data);
  };

  const handleCreateDelivery = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = {
      product_id: parseInt(formData.get('product_id') as string),
      quantity: parseInt(formData.get('quantity') as string),
      delivery_date: formData.get('delivery_date') as string,
      supplier: formData.get('supplier') as string,
      price: parseFloat(formData.get('price') as string)
    };
    createDeliveryMutation.mutate(data);
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
        <div className="text-center text-red-600">Mahsulotlarni yuklashda xatolik yuz berdi</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Mahsulotlar</h1>
          <p className="text-gray-600">Ombordagi mahsulotlarni boshqarish</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={isDeliveryDialogOpen} onOpenChange={setIsDeliveryDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Truck className="h-4 w-4 mr-2" />
                Yetkazib berish
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Yangi yetkazib berish</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateDelivery} className="space-y-4">
                <div>
                  <Label htmlFor="product_id">Mahsulot</Label>
                  <Select name="product_id" required>
                    <SelectTrigger>
                      <SelectValue placeholder="Mahsulotni tanlang" />
                    </SelectTrigger>
                    <SelectContent>
                      {products.map((product: Product) => (
                        <SelectItem key={product.id} value={product.id.toString()}>
                          {product.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="quantity">Miqdor</Label>
                  <Input name="quantity" type="number" min="1" required />
                </div>
                <div>
                  <Label htmlFor="delivery_date">Yetkazib berish sanasi</Label>
                  <Input name="delivery_date" type="date" required />
                </div>
                <div>
                  <Label htmlFor="supplier">Yetkazib beruvchi</Label>
                  <Input name="supplier" required />
                </div>
                <div>
                  <Label htmlFor="price">Narx</Label>
                  <Input name="price" type="number" step="0.01" min="0" required />
                </div>
                <Button type="submit" disabled={createDeliveryMutation.isPending}>
                  {createDeliveryMutation.isPending ? 'Qo\'shilmoqda...' : 'Qo\'shish'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
          
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Yangi mahsulot
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Yangi mahsulot yaratish</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateProduct} className="space-y-4">
                <div>
                  <Label htmlFor="name">Nomi</Label>
                  <Input name="name" required />
                </div>
                <div>
                  <Label htmlFor="unit_id">O'lchov birligi</Label>
                  <Select name="unit_id" required>
                    <SelectTrigger>
                      <SelectValue placeholder="Birlikni tanlang" />
                    </SelectTrigger>
                    <SelectContent>
                      {units.map((unit: Unit) => (
                        <SelectItem key={unit.id} value={unit.id.toString()}>
                          {unit.name} ({unit.short_name})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label htmlFor="min_quantity">Minimal miqdor</Label>
                  <Input name="min_quantity" type="number" min="0" required />
                </div>
                <Button type="submit" disabled={createProductMutation.isPending}>
                  {createProductMutation.isPending ? 'Yaratilmoqda...' : 'Yaratish'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <Input
                  placeholder="Mahsulot qidirish..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Button
              variant={showLowStockOnly ? "default" : "outline"}
              onClick={() => setShowLowStockOnly(!showLowStockOnly)}
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Kam qolganlar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Products Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product: Product) => (
          <Card key={product.id} className="hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <CardTitle className="text-lg">{product.name}</CardTitle>
                <Package className="h-5 w-5 text-gray-400" />
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-sm">
                <span>O'lchov:</span>
                <span>{product.unit.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Minimal:</span>
                <span>{product.min_quantity} {product.unit.short_name}</span>
              </div>
              {product.current_quantity !== undefined && (
                <div className="flex justify-between text-sm">
                  <span>Mavjud:</span>
                  <Badge variant={product.current_quantity <= product.min_quantity ? "destructive" : "secondary"}>
                    {product.current_quantity} {product.unit.short_name}
                  </Badge>
                </div>
              )}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleViewDetails(product.id)}
                  className="flex-1"
                >
                  <Eye className="h-3 w-3 mr-1" />
                  Ko'rish
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleEditProduct(product)}
                >
                  <Edit className="h-3 w-3" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDeleteProduct(product.id)}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Edit Product Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Mahsulotni tahrirlash</DialogTitle>
          </DialogHeader>
          {editingProduct && (
            <form onSubmit={handleUpdateProduct} className="space-y-4">
              <div>
                <Label htmlFor="name">Nomi</Label>
                <Input name="name" defaultValue={editingProduct.name} required />
              </div>
              <div>
                <Label htmlFor="unit_id">O'lchov birligi</Label>
                <Select name="unit_id" defaultValue={editingProduct.unit.id.toString()} required>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {units.map((unit: Unit) => (
                      <SelectItem key={unit.id} value={unit.id.toString()}>
                        {unit.name} ({unit.short_name})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="min_quantity">Minimal miqdor</Label>
                <Input name="min_quantity" type="number" min="0" defaultValue={editingProduct.min_quantity} required />
              </div>
              <Button type="submit" disabled={updateProductMutation.isPending}>
                {updateProductMutation.isPending ? 'Yangilanmoqda...' : 'Yangilash'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Product Details Dialog */}
      <Dialog open={isDetailsDialogOpen} onOpenChange={setIsDetailsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Mahsulot tafsilotlari</DialogTitle>
          </DialogHeader>
          {detailsLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : productDetails ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Nomi</Label>
                  <p className="font-medium">{productDetails.name}</p>
                </div>
                <div>
                  <Label>O'lchov birligi</Label>
                  <p>{productDetails.unit.name} ({productDetails.unit.short_name})</p>
                </div>
                <div>
                  <Label>Minimal miqdor</Label>
                  <p>{productDetails.min_quantity} {productDetails.unit.short_name}</p>
                </div>
                {productDetails.current_quantity !== undefined && (
                  <div>
                    <Label>Hozirgi miqdor</Label>
                    <p>{productDetails.current_quantity} {productDetails.unit.short_name}</p>
                  </div>
                )}
                <div>
                  <Label>Yaratilgan</Label>
                  <p>{formatDate(productDetails.created_at)}</p>
                </div>
                <div>
                  <Label>Yaratgan</Label>
                  <p>{productDetails.created_by_user.full_name}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Mahsulot tafsilotlari yuklanmadi
            </div>
          )}
        </DialogContent>
      </Dialog>

      {products.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Package className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">Mahsulotlar topilmadi</h3>
            <p className="text-gray-600">
              {searchQuery || showLowStockOnly 
                ? "Qidiruv shartlariga mos mahsulotlar topilmadi"
                : "Hali mahsulotlar qo'shilmagan"
              }
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ProductsPage;
