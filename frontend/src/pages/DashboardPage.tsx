import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import {
  Package,
  FolderOpen,
  Warehouse,
  AlertTriangle,
  Plus,
  ArrowRightLeft,
  ExternalLink,
  Activity,
  TrendingUp,
} from 'lucide-react';
import { StatsCard } from '@/components/StatsCard';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useShowcaseStats, useStockLevels, useCategories, useAuditLog } from '@/hooks/useApi';

interface StockLevel {
  id: string;
  product_id: string;
  warehouse_id: string;
  quantity: number;
  low_stock_threshold: number;
  product: {
    name: string;
    category: {
      name: string;
    };
  };
  warehouse: {
    name: string;
    code: string;
  };
}

interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  product_count?: number;
}

interface AuditLogEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  created_at: string;
  user: {
    username: string;
    email: string;
  };
}

export default function DashboardPage() {
  const { data: showcaseStats, isLoading: statsLoading } = useShowcaseStats();
  const { data: stockData, isLoading: stockLoading } = useStockLevels();
  const { data: categories, isLoading: categoriesLoading } = useCategories();
  const { data: auditData, isLoading: auditLoading } = useAuditLog({}, 1);

  // Process data for charts
  const stockByWarehouse = useMemo(() => {
    if (!stockData?.items) return [];

    const warehouseStock: Record<string, { name: string; totalStock: number }> = {};

    (stockData.items as StockLevel[]).forEach((stock) => {
      const warehouseName = stock.warehouse.name;
      if (!warehouseStock[warehouseName]) {
        warehouseStock[warehouseName] = {
          name: warehouseName,
          totalStock: 0,
        };
      }
      warehouseStock[warehouseName].totalStock += stock.quantity;
    });

    return Object.values(warehouseStock);
  }, [stockData]);

  const productsByCategory = useMemo(() => {
    if (!categories) return [];

    return (categories as Category[])
      .filter(cat => cat.product_count && cat.product_count > 0)
      .map(cat => ({
        name: cat.name,
        value: cat.product_count || 0,
      }))
      .slice(0, 6); // Limit to top 6 categories for better visualization
  }, [categories]);

  const auditActivity = useMemo(() => {
    if (!auditData?.items) return [];

    const activityByDate: Record<string, number> = {};

    (auditData.items as AuditLogEntry[]).forEach((entry) => {
      const date = new Date(entry.created_at).toLocaleDateString();
      activityByDate[date] = (activityByDate[date] || 0) + 1;
    });

    return Object.entries(activityByDate)
      .map(([date, count]) => ({
        date,
        activity: count,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .slice(-7); // Last 7 days
  }, [auditData]);

  const recentActivity = useMemo(() => {
    if (!auditData?.items) return [];
    return (auditData.items as AuditLogEntry[]).slice(0, 5);
  }, [auditData]);

  // Chart colors for consistent theming
  const CHART_COLORS = [
    'hsl(var(--chart-1))',
    'hsl(var(--chart-2))',
    'hsl(var(--chart-3))',
    'hsl(var(--chart-4))',
    'hsl(var(--chart-5))',
  ];

  const formatActionText = (action: string, resourceType: string) => {
    const actionMap: Record<string, string> = {
      create: 'Created',
      update: 'Updated',
      delete: 'Deleted',
      transfer: 'Transferred',
    };

    return `${actionMap[action] || action} ${resourceType.toLowerCase()}`;
  };

  const getActionColor = (action: string) => {
    const colorMap: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      create: 'default',
      update: 'secondary',
      delete: 'destructive',
      transfer: 'outline',
    };

    return colorMap[action] || 'default';
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of your inventory management system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-green-600" />
          <span className="text-sm text-muted-foreground">Live data</span>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <Skeleton className="h-4 w-[100px]" />
                <Skeleton className="h-4 w-4" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-7 w-[60px] mb-1" />
                <Skeleton className="h-3 w-[80px]" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <StatsCard
              title="Total Products"
              value={showcaseStats?.total_products || 0}
              icon={Package}
              description="Active inventory items"
            />
            <StatsCard
              title="Categories"
              value={showcaseStats?.total_categories || 0}
              icon={FolderOpen}
              description="Product categorization"
            />
            <StatsCard
              title="Warehouses"
              value={showcaseStats?.total_warehouses || 0}
              icon={Warehouse}
              description="Storage locations"
            />
            <StatsCard
              title="Low Stock Alerts"
              value={showcaseStats?.low_stock_alerts || 0}
              icon={AlertTriangle}
              description="Items need restocking"
              trend={showcaseStats?.low_stock_alerts ? 'down' : 'neutral'}
            />
          </>
        )}
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Stock by Warehouse Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Stock Levels by Warehouse</CardTitle>
          </CardHeader>
          <CardContent>
            {stockLoading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={stockByWarehouse}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Bar
                    dataKey="totalStock"
                    fill="hsl(var(--chart-1))"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Products by Category Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Products by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {categoriesLoading ? (
              <Skeleton className="h-[300px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={productsByCategory}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                    label={(entry) => entry.name}
                  >
                    {productsByCategory.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Audit Activity Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {auditLoading ? (
            <Skeleton className="h-[200px] w-full" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={auditActivity}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="activity"
                  stroke="hsl(var(--chart-3))"
                  fill="hsl(var(--chart-3))"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Activity Feed */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {auditLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded-full" />
                    <div className="space-y-1">
                      <Skeleton className="h-4 w-[200px]" />
                      <Skeleton className="h-3 w-[150px]" />
                    </div>
                  </div>
                ))}
              </div>
            ) : recentActivity.length > 0 ? (
              <div className="space-y-4">
                {recentActivity.map((entry, index) => (
                  <div key={entry.id}>
                    <div className="flex items-start gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                        <Activity className="h-4 w-4" />
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={getActionColor(entry.action)}>
                            {formatActionText(entry.action, entry.resource_type)}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            by {entry.user.username}
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {new Date(entry.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {index < recentActivity.length - 1 && (
                      <Separator className="mt-4" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No recent activity</p>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" size="sm">
              <Plus className="mr-2 h-4 w-4" />
              Add Product
            </Button>
            <Button variant="outline" className="w-full justify-start" size="sm">
              <ArrowRightLeft className="mr-2 h-4 w-4" />
              Transfer Stock
            </Button>
            <Button variant="outline" className="w-full justify-start" size="sm">
              <ExternalLink className="mr-2 h-4 w-4" />
              View API Docs
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}