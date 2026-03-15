import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Package,
  FolderTree,
  Warehouse,
  ArrowLeftRight,
  AlertTriangle,
  Search,
  Shield,
  Database,
  ExternalLink
} from 'lucide-react';

interface ShowcaseStats {
  total_products: number;
  total_categories: number;
  total_warehouses: number;
  total_stock_transfers: number;
  low_stock_alerts: number;
}

export default function LandingPage() {
  const [stats, setStats] = useState<ShowcaseStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/showcase/stats');
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  const techStack = [
    { name: 'Python 3.13', variant: 'default' as const },
    { name: 'FastAPI', variant: 'secondary' as const },
    { name: 'SQLAlchemy', variant: 'default' as const },
    { name: 'PostgreSQL', variant: 'secondary' as const },
    { name: 'React 19', variant: 'default' as const },
    { name: 'TypeScript', variant: 'secondary' as const },
  ];

  const features = [
    {
      icon: Search,
      title: 'Full-Text Search',
      description: 'PostgreSQL TSVECTOR with GIN indexing for lightning-fast product search with relevance ranking.',
    },
    {
      icon: ArrowLeftRight,
      title: 'Atomic Stock Transfers',
      description: 'SELECT FOR UPDATE transactions ensure data consistency during inventory movements between warehouses.',
    },
    {
      icon: Database,
      title: 'Audit Logging',
      description: 'Complete activity trail with user tracking, IP addresses, and detailed change records for compliance.',
    },
    {
      icon: Shield,
      title: 'Dual Authentication',
      description: 'JWT tokens for interactive use and API keys for programmatic access with bcrypt password security.',
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-muted/20" />
        <div className="relative container mx-auto px-6 pt-16 pb-24 text-center">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent mb-6">
              ShipAPI
            </h1>
            <p className="text-xl md:text-2xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Production-grade inventory management API
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button asChild size="lg" className="text-lg px-8 py-6">
                <a href="/login">Try the Demo</a>
              </Button>
              <Button asChild variant="outline" size="lg" className="text-lg px-8 py-6">
                <a href="/docs" target="_blank" rel="noopener noreferrer">
                  View API Docs
                  <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Live Stats Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Live Database Metrics</h2>
          <p className="text-muted-foreground">Real-time statistics from our production database</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
          <Card className="text-center">
            <CardHeader className="flex flex-col items-center space-y-0 pb-2">
              <Package className="h-8 w-8 text-muted-foreground mb-2" />
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Products
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {isLoading ? '—' : stats?.total_products?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader className="flex flex-col items-center space-y-0 pb-2">
              <FolderTree className="h-8 w-8 text-muted-foreground mb-2" />
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Categories
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {isLoading ? '—' : stats?.total_categories?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader className="flex flex-col items-center space-y-0 pb-2">
              <Warehouse className="h-8 w-8 text-muted-foreground mb-2" />
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Warehouses
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {isLoading ? '—' : stats?.total_warehouses?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader className="flex flex-col items-center space-y-0 pb-2">
              <ArrowLeftRight className="h-8 w-8 text-muted-foreground mb-2" />
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Stock Transfers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">
                {isLoading ? '—' : stats?.total_stock_transfers?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader className="flex flex-col items-center space-y-0 pb-2">
              <AlertTriangle className="h-8 w-8 text-yellow-500 mb-2" />
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Low Stock Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-500">
                {isLoading ? '—' : stats?.low_stock_alerts?.toLocaleString() || '0'}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Features Section */}
      <div className="container mx-auto px-6 py-16 bg-muted/30">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Key Capabilities</h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Enterprise-grade features built for scale, reliability, and performance
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Card key={index} className="h-full">
              <CardHeader>
                <feature.icon className="h-12 w-12 text-primary mb-4" />
                <CardTitle className="text-xl">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Tech Stack Section */}
      <div className="container mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Modern Tech Stack</h2>
          <p className="text-muted-foreground">
            Built with cutting-edge technologies for performance and developer experience
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {techStack.map((tech) => (
            <Badge key={tech.name} variant={tech.variant} className="text-sm py-2 px-4">
              {tech.name}
            </Badge>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-muted/20">
        <div className="container mx-auto px-6 py-8 text-center">
          <p className="text-muted-foreground">
            Built by{' '}
            <a
              href="https://workermill.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline font-medium"
            >
              WorkerMill
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}