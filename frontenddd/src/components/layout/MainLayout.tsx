
import { useState } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { 
  Home, 
  Package, 
  ChefHat, 
  Users, 
  BarChart3, 
  Bell, 
  Settings,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';

const MainLayout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home, roles: ['admin', 'menejer', 'oshpaz'] },
    { name: 'Mahsulotlar', href: '/products', icon: Package, roles: ['admin', 'menejer'] },
    { name: 'Ovqatlar', href: '/meals', icon: ChefHat, roles: ['admin', 'menejer'] },
    { name: 'Ovqat Berish', href: '/servings', icon: ChefHat, roles: ['admin', 'menejer', 'oshpaz'] },
    { name: 'Foydalanuvchilar', href: '/users', icon: Users, roles: ['admin'] },
    { name: 'Hisobotlar', href: '/reports', icon: BarChart3, roles: ['admin', 'menejer'] },
    { name: 'Bildirishnomalar', href: '/notifications', icon: Bell, roles: ['admin', 'menejer', 'oshpaz'] },
  ];

  const filteredNavigation = navigation.filter(item => 
    user && item.roles.includes(user.role.name)
  );

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className={cn(
        "bg-white shadow-lg transition-all duration-300 flex flex-col",
        isSidebarOpen ? "w-64" : "w-16"
      )}>
        {/* Logo and Toggle */}
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          {isSidebarOpen && (
            <h1 className="text-xl font-bold text-green-700">Bog'cha Tizimi</h1>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            {isSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {filteredNavigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  "flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-green-100 text-green-700"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )}
              >
                <item.icon className={cn("h-5 w-5", isSidebarOpen ? "mr-3" : "mx-auto")} />
                {isSidebarOpen && item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Info and Logout */}
        <div className="p-4 border-t border-gray-200">
          {isSidebarOpen && user && (
            <div className="mb-3">
              <p className="text-sm font-medium text-gray-900">{user.full_name}</p>
              <p className="text-xs text-gray-500">{user.role.name}</p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className={cn("w-full text-red-600 hover:text-red-700 hover:bg-red-50", 
              !isSidebarOpen && "justify-center"
            )}
          >
            <LogOut className={cn("h-4 w-4", isSidebarOpen ? "mr-2" : "")} />
            {isSidebarOpen && "Chiqish"}
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
