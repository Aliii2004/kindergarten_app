
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { Search, Users, Eye, UserPlus, Edit, Trash2 } from 'lucide-react';
import { userService } from '@/services/userService';

const UsersPage = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateUserDialogOpen, setIsCreateUserDialogOpen] = useState(false);
  const [isEditUserDialogOpen, setIsEditUserDialogOpen] = useState(false);
  const [isUserDetailsDialogOpen, setIsUserDetailsDialogOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [editingUser, setEditingUser] = useState<any>(null);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch current user
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      return await userService.getCurrentUser();
    }
  });

  // Fetch all users
  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      return await userService.getUsers();
    }
  });

  // Fetch roles
  const { data: roles = [], isLoading: rolesLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: async () => {
      return await userService.getRoles();
    }
  });

  // Fetch user details
  const { data: userDetails, isLoading: userDetailsLoading } = useQuery({
    queryKey: ['user-details', selectedUserId],
    queryFn: async () => {
      if (!selectedUserId) return null;
      return await userService.getUser(selectedUserId);
    },
    enabled: !!selectedUserId && isUserDetailsDialogOpen
  });

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: async (data: { username: string; full_name: string; password: string; role_id: number }) => {
      return await userService.createUser(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setIsCreateUserDialogOpen(false);
      toast({
        title: "Muvaffaqiyat",
        description: "Foydalanuvchi muvaffaqiyatli yaratildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Foydalanuvchi yaratishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Update user mutation
  const updateUserMutation = useMutation({
    mutationFn: async (data: { id: number; username: string; full_name: string; role_id: number; is_active: boolean }) => {
      const { id, ...updateData } = data;
      return await userService.updateUser(id, updateData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      queryClient.invalidateQueries({ queryKey: ['current-user'] });
      setIsEditUserDialogOpen(false);
      setEditingUser(null);
      toast({
        title: "Muvaffaqiyat",
        description: "Foydalanuvchi muvaffaqiyatli yangilandi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Foydalanuvchini yangilashda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: async (userId: number) => {
      return await userService.deleteUser(userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast({
        title: "Muvaffaqiyat",
        description: "Foydalanuvchi muvaffaqiyatli o'chirildi"
      });
    },
    onError: (error: any) => {
      toast({
        title: "Xatolik",
        description: error.response?.data?.detail || "Foydalanuvchini o'chirishda xatolik yuz berdi",
        variant: "destructive"
      });
    }
  });

  const handleViewUserDetails = (userId: number) => {
    setSelectedUserId(userId);
    setIsUserDetailsDialogOpen(true);
  };

  const handleEditUser = (user: any) => {
    setEditingUser(user);
    setIsEditUserDialogOpen(true);
  };

  const handleDeleteUser = (userId: number) => {
    if (currentUser && userId === currentUser.id) {
      toast({
        title: "Xatolik",
        description: "O'zingizni o'chira olmaysiz",
        variant: "destructive"
      });
      return;
    }
    
    if (confirm('Bu foydalanuvchini o\'chirishni tasdiqlaysizmi?')) {
      deleteUserMutation.mutate(userId);
    }
  };

  const handleCreateUser = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = {
      username: formData.get('username') as string,
      full_name: formData.get('full_name') as string,
      password: formData.get('password') as string,
      role_id: parseInt(formData.get('role_id') as string)
    };
    createUserMutation.mutate(data);
  };

  const handleUpdateUser = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingUser) return;

    const formData = new FormData(e.currentTarget);
    const data = {
      id: editingUser.id,
      username: formData.get('username') as string,
      full_name: formData.get('full_name') as string,
      role_id: parseInt(formData.get('role_id') as string),
      is_active: formData.get('is_active') === 'on'
    };
    updateUserMutation.mutate(data);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Noma\'lum sana';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return 'Noma\'lum sana';
      return date.toLocaleDateString('uz-UZ', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      });
    } catch (error) {
      return 'Noma\'lum sana';
    }
  };

  const filteredUsers = users.filter((user: any) => 
    user.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Foydalanuvchilar</h1>
          <p className="text-gray-600">Tizim foydalanuvchilarini boshqarish</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={isCreateUserDialogOpen} onOpenChange={setIsCreateUserDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="h-4 w-4 mr-2" />
                Yangi foydalanuvchi
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Yangi foydalanuvchi yaratish</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreateUser} className="space-y-4">
                <div>
                  <Label htmlFor="username">Foydalanuvchi nomi</Label>
                  <Input name="username" required />
                </div>
                <div>
                  <Label htmlFor="full_name">To'liq ism</Label>
                  <Input name="full_name" required />
                </div>
                <div>
                  <Label htmlFor="password">Parol</Label>
                  <Input name="password" type="password" required />
                </div>
                <div>
                  <Label htmlFor="role_id">Rol</Label>
                  <Select name="role_id" required>
                    <SelectTrigger>
                      <SelectValue placeholder="Rolni tanlang" />
                    </SelectTrigger>
                    <SelectContent>
                      {roles.map((role: any) => (
                        <SelectItem key={role.id} value={role.id.toString()}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button type="submit" disabled={createUserMutation.isPending}>
                  {createUserMutation.isPending ? 'Yaratilmoqda...' : 'Yaratish'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Current User Info */}
      {currentUser && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Users className="h-5 w-5 mr-2" />
              Joriy foydalanuvchi
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <Label>To'liq ism</Label>
                <p className="font-medium">{currentUser.full_name}</p>
              </div>
              <div>
                <Label>Foydalanuvchi nomi</Label>
                <p>{currentUser.username}</p>
              </div>
              <div>
                <Label>Rol</Label>
                <Badge>{currentUser.role?.name || 'Noma\'lum rol'}</Badge>
              </div>
              <div>
                <Label>Yaratilgan</Label>
                <p>{formatDate(currentUser.created_at)}</p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleViewUserDetails(currentUser.id)}
              className="mt-4"
            >
              <Eye className="h-4 w-4 mr-2" />
              Batafsil ko'rish
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Foydalanuvchi qidirish..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Users List */}
      <Card>
        <CardHeader>
          <CardTitle>Barcha foydalanuvchilar</CardTitle>
        </CardHeader>
        <CardContent>
          {usersLoading ? (
            <div className="text-center py-4">Yuklanmoqda...</div>
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-8">
              <UserPlus className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Foydalanuvchilar topilmadi</h3>
              <p className="text-gray-600">
                {searchQuery ? "Qidiruv shartlariga mos foydalanuvchilar topilmadi" : "Hali foydalanuvchilar yaratilmagan"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredUsers.map((user: any) => (
                <div key={user.id} className="p-3 border rounded flex justify-between items-center">
                  <div>
                    <p className="font-medium">{user.full_name}</p>
                    <p className="text-sm text-gray-600">{user.username}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline">{user.role?.name || 'Noma\'lum rol'}</Badge>
                      <Badge variant={user.is_active ? "default" : "secondary"}>
                        {user.is_active ? "Faol" : "Nofaol"}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleViewUserDetails(user.id)}
                    >
                      <Eye className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditUser(user)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteUser(user.id)}
                      className="text-red-600 hover:text-red-700"
                      disabled={currentUser && user.id === currentUser.id}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Roles Section */}
      <Card>
        <CardHeader>
          <CardTitle>Rollar</CardTitle>
        </CardHeader>
        <CardContent>
          {rolesLoading ? (
            <div className="text-center py-4">Yuklanmoqda...</div>
          ) : roles.length === 0 ? (
            <div className="text-center py-8">
              <UserPlus className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Rollar topilmadi</h3>
              <p className="text-gray-600">Hali rollar yaratilmagan</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {roles.map((role: any) => (
                <Card key={role.id} className="p-4">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium">{role.name}</h3>
                      {role.description && (
                        <p className="text-sm text-gray-600 mt-1">{role.description}</p>
                      )}
                    </div>
                    <Badge variant="outline">{role.id}</Badge>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit User Dialog */}
      <Dialog open={isEditUserDialogOpen} onOpenChange={setIsEditUserDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Foydalanuvchini tahrirlash</DialogTitle>
          </DialogHeader>
          {editingUser && (
            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <Label htmlFor="username">Foydalanuvchi nomi</Label>
                <Input name="username" defaultValue={editingUser.username} required />
              </div>
              <div>
                <Label htmlFor="full_name">To'liq ism</Label>
                <Input name="full_name" defaultValue={editingUser.full_name} required />
              </div>
              <div>
                <Label htmlFor="role_id">Rol</Label>
                <Select name="role_id" defaultValue={editingUser.role?.id?.toString()} required>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map((role: any) => (
                      <SelectItem key={role.id} value={role.id.toString()}>
                        {role.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center space-x-2">
                <Switch name="is_active" id="is_active" defaultChecked={editingUser.is_active} />
                <Label htmlFor="is_active">Faol</Label>
              </div>
              <Button type="submit" disabled={updateUserMutation.isPending}>
                {updateUserMutation.isPending ? 'Yangilanmoqda...' : 'Yangilash'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* User Details Dialog */}
      <Dialog open={isUserDetailsDialogOpen} onOpenChange={setIsUserDetailsDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Foydalanuvchi tafsilotlari</DialogTitle>
          </DialogHeader>
          {userDetailsLoading ? (
            <div className="text-center py-8">Yuklanmoqda...</div>
          ) : userDetails ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>ID</Label>
                  <p className="font-medium">{userDetails.id}</p>
                </div>
                <div>
                  <Label>To'liq ism</Label>
                  <p className="font-medium">{userDetails.full_name}</p>
                </div>
                <div>
                  <Label>Foydalanuvchi nomi</Label>
                  <p>{userDetails.username}</p>
                </div>
                <div>
                  <Label>Rol</Label>
                  <div className="flex items-center gap-2">
                    <Badge>{userDetails.role?.name || 'Noma\'lum rol'}</Badge>
                  </div>
                </div>
                <div>
                  <Label>Faol</Label>
                  <Badge variant={userDetails.is_active ? "default" : "secondary"}>
                    {userDetails.is_active ? "Ha" : "Yo'q"}
                  </Badge>
                </div>
                <div>
                  <Label>Yaratilgan</Label>
                  <p>{formatDate(userDetails.created_at)}</p>
                </div>
                {userDetails.role?.description && (
                  <div className="col-span-2">
                    <Label>Rol tavsifi</Label>
                    <p className="text-gray-600">{userDetails.role.description}</p>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Foydalanuvchi tafsilotlari yuklanmadi
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UsersPage;
