import { NavLink, useLocation } from 'react-router';
import {
  LayoutDashboard,
  Package,
  FolderOpen,
  Warehouse,
  BarChart3,
  Activity,
  FileText,
  LogOut
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Products',
    href: '/dashboard/products',
    icon: Package,
  },
  {
    name: 'Categories',
    href: '/dashboard/categories',
    icon: FolderOpen,
  },
  {
    name: 'Warehouses',
    href: '/dashboard/warehouses',
    icon: Warehouse,
  },
  {
    name: 'Stock',
    href: '/dashboard/stock',
    icon: BarChart3,
  },
  {
    name: 'Audit',
    href: '/dashboard/audit',
    icon: Activity,
  },
  {
    name: 'API Docs',
    href: '/dashboard/api-docs',
    icon: FileText,
  },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="flex flex-col h-full bg-card border-r border-border">
      {/* Logo/Brand */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center space-x-2">
          <Package className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg">ShipAPI</span>
        </div>
      </div>

      {/* User Info */}
      {user && (
        <div className="p-4 border-b border-border">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium text-primary">
                {user.username.charAt(0).toUpperCase()}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user.username}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-4 py-4 space-y-1">
        {navigationItems.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={cn(
                'flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-4">
        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-foreground"
          onClick={logout}
        >
          <LogOut className="h-4 w-4 mr-3" />
          Sign out
        </Button>

        <Separator />

        {/* Built by WorkerMill */}
        <div className="text-center">
          <a
            href="https://workermill.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Built by WorkerMill
          </a>
        </div>
      </div>
    </div>
  );
}