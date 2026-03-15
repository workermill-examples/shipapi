import { useState } from 'react';
import { ExternalLink, Book, FileText, Code2, Zap } from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';

export default function ApiDocsPage() {
  const [selectedTab, setSelectedTab] = useState('overview');

  // API documentation URLs - these should point to the backend docs
  const swaggerUrl = '/docs';
  const redocUrl = '/redoc';

  const apiEndpoints = [
    {
      category: 'Authentication',
      description: 'User registration, login, JWT refresh, and API key management',
      endpoints: [
        'POST /api/v1/auth/register',
        'POST /api/v1/auth/login',
        'POST /api/v1/auth/refresh',
        'GET /api/v1/auth/me',
        'POST /api/v1/auth/api-key',
        'DELETE /api/v1/auth/api-key',
      ]
    },
    {
      category: 'Products',
      description: 'Product catalog management with search and filtering',
      endpoints: [
        'GET /api/v1/products',
        'POST /api/v1/products',
        'GET /api/v1/products/{id}',
        'PUT /api/v1/products/{id}',
        'DELETE /api/v1/products/{id}',
      ]
    },
    {
      category: 'Categories',
      description: 'Product categories with hierarchical structure',
      endpoints: [
        'GET /api/v1/categories',
        'POST /api/v1/categories',
        'GET /api/v1/categories/{id}',
        'PUT /api/v1/categories/{id}',
        'DELETE /api/v1/categories/{id}',
      ]
    },
    {
      category: 'Warehouses',
      description: 'Warehouse management and stock summaries',
      endpoints: [
        'GET /api/v1/warehouses',
        'POST /api/v1/warehouses',
        'GET /api/v1/warehouses/{id}',
        'PUT /api/v1/warehouses/{id}',
        'DELETE /api/v1/warehouses/{id}',
      ]
    },
    {
      category: 'Stock Management',
      description: 'Inventory levels, transfers, and adjustments',
      endpoints: [
        'GET /api/v1/stock',
        'GET /api/v1/stock/alerts',
        'PUT /api/v1/stock/adjust',
        'POST /api/v1/stock/transfers',
        'GET /api/v1/stock/transfers',
      ]
    },
    {
      category: 'Audit',
      description: 'Activity tracking and audit logs',
      endpoints: [
        'GET /api/v1/audit',
      ]
    },
    {
      category: 'System',
      description: 'Health checks and system status',
      endpoints: [
        'GET /api/v1/health',
        'GET /showcase/stats',
      ]
    }
  ];

  const features = [
    {
      icon: <Zap className="h-5 w-5" />,
      title: 'FastAPI Framework',
      description: 'Built with FastAPI for high performance and automatic OpenAPI generation'
    },
    {
      icon: <Code2 className="h-5 w-5" />,
      title: 'JWT + API Key Auth',
      description: 'Secure authentication with JSON Web Tokens and API key support'
    },
    {
      icon: <Book className="h-5 w-5" />,
      title: 'PostgreSQL Database',
      description: 'Production-ready PostgreSQL with full-text search and ACID transactions'
    },
    {
      icon: <FileText className="h-5 w-5" />,
      title: 'Comprehensive Docs',
      description: 'Auto-generated OpenAPI 3.0 documentation with interactive examples'
    }
  ];

  return (
    <div className="container mx-auto px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-3xl">API Documentation</CardTitle>
          <CardDescription className="text-lg">
            Complete REST API reference for the ShipAPI inventory management system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
              <TabsTrigger value="docs">Documentation</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              <div>
                <h3 className="text-2xl font-semibold mb-4">ShipAPI Overview</h3>
                <p className="text-muted-foreground leading-relaxed mb-6">
                  ShipAPI is a production-grade inventory management REST API built with FastAPI.
                  It provides comprehensive functionality for managing products, categories, warehouses,
                  stock levels, and audit trails. The API features JWT authentication, full-text search,
                  atomic stock transfers, and comprehensive audit logging.
                </p>
              </div>

              <div>
                <h4 className="text-lg font-semibold mb-4">Key Features</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {features.map((feature, index) => (
                    <div key={index} className="flex items-start space-x-3 p-4 rounded-lg border bg-muted/20">
                      <div className="text-primary">{feature.icon}</div>
                      <div>
                        <h5 className="font-medium">{feature.title}</h5>
                        <p className="text-sm text-muted-foreground mt-1">
                          {feature.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <Separator />

              <div>
                <h4 className="text-lg font-semibold mb-4">Quick Start</h4>
                <div className="space-y-4">
                  <div className="bg-muted rounded-lg p-4">
                    <h5 className="font-medium mb-2">1. Authentication</h5>
                    <p className="text-sm text-muted-foreground">
                      Register or login to get a JWT token, or generate an API key for programmatic access.
                    </p>
                  </div>
                  <div className="bg-muted rounded-lg p-4">
                    <h5 className="font-medium mb-2">2. Explore Endpoints</h5>
                    <p className="text-sm text-muted-foreground">
                      Use the interactive Swagger UI to explore all available endpoints and test requests.
                    </p>
                  </div>
                  <div className="bg-muted rounded-lg p-4">
                    <h5 className="font-medium mb-2">3. Integration</h5>
                    <p className="text-sm text-muted-foreground">
                      Include your JWT token in the Authorization header or API key in X-API-Key header.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
                <h5 className="font-medium text-orange-800 dark:text-orange-200 mb-2">Demo Credentials</h5>
                <div className="text-sm text-orange-700 dark:text-orange-300 space-y-1">
                  <p><strong>Email:</strong> demo@workermill.com</p>
                  <p><strong>Password:</strong> demo1234</p>
                  <p className="text-xs mt-2">
                    Use these credentials to explore the API with admin privileges.
                  </p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="endpoints" className="space-y-6">
              <div>
                <h3 className="text-2xl font-semibold mb-4">API Endpoints</h3>
                <p className="text-muted-foreground mb-6">
                  All endpoints are available under the <code className="bg-muted px-2 py-1 rounded">/api/v1</code> prefix.
                </p>
              </div>

              <div className="space-y-6">
                {apiEndpoints.map((category, index) => (
                  <Card key={index}>
                    <CardHeader>
                      <CardTitle className="text-lg">{category.category}</CardTitle>
                      <CardDescription>{category.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {category.endpoints.map((endpoint, endpointIndex) => (
                          <div key={endpointIndex} className="flex items-center space-x-3">
                            <Badge variant="outline" className="font-mono text-xs min-w-[60px]">
                              {endpoint.split(' ')[0]}
                            </Badge>
                            <code className="text-sm bg-muted px-2 py-1 rounded flex-1">
                              {endpoint.split(' ')[1]}
                            </code>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="docs" className="space-y-6">
              <div>
                <h3 className="text-2xl font-semibold mb-4">Interactive Documentation</h3>
                <p className="text-muted-foreground mb-6">
                  Access the interactive API documentation to explore endpoints, test requests,
                  and view detailed schemas and examples.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Book className="h-5 w-5" />
                      <span>Swagger UI</span>
                    </CardTitle>
                    <CardDescription>
                      Interactive API explorer with request/response examples and testing capabilities
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                        <div className="text-center">
                          <Book className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-sm text-muted-foreground">Swagger UI Preview</p>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button asChild className="flex-1">
                          <a href={swaggerUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-4 w-4 mr-2" />
                            Open Swagger UI
                          </a>
                        </Button>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        <p>• Test API endpoints directly in your browser</p>
                        <p>• View request/response schemas</p>
                        <p>• Copy curl commands for integration</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <FileText className="h-5 w-5" />
                      <span>ReDoc</span>
                    </CardTitle>
                    <CardDescription>
                      Clean, readable API reference documentation with detailed descriptions
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="aspect-video bg-muted rounded-lg flex items-center justify-center">
                        <div className="text-center">
                          <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-sm text-muted-foreground">ReDoc Preview</p>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button asChild variant="outline" className="flex-1">
                          <a href={redocUrl} target="_blank" rel="noopener noreferrer">
                            <ExternalLink className="h-4 w-4 mr-2" />
                            Open ReDoc
                          </a>
                        </Button>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        <p>• Beautiful, three-panel layout</p>
                        <p>• Comprehensive endpoint documentation</p>
                        <p>• Easy navigation and search</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Separator />

              <Card>
                <CardHeader>
                  <CardTitle>Authentication</CardTitle>
                  <CardDescription>
                    How to authenticate your API requests
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h5 className="font-medium mb-2">JWT Token (Recommended for browser apps)</h5>
                    <div className="bg-muted rounded-lg p-3">
                      <code className="text-sm">Authorization: Bearer &lt;your_jwt_token&gt;</code>
                    </div>
                  </div>
                  <div>
                    <h5 className="font-medium mb-2">API Key (Recommended for server-to-server)</h5>
                    <div className="bg-muted rounded-lg p-3">
                      <code className="text-sm">X-API-Key: sk_&lt;your_api_key&gt;</code>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <p>
                      Both authentication methods provide access to the same endpoints.
                      JWT tokens expire and can be refreshed, while API keys are long-lived
                      until manually revoked.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}