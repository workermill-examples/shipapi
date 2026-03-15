import { Routes, Route } from 'react-router';
import { AuthContext, useAuthProvider } from '@/hooks/useAuth';
import { Toaster } from '@/components/ui/sonner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ProductsPage from '@/pages/ProductsPage';
import CategoriesPage from '@/pages/CategoriesPage';
import WarehousesPage from '@/pages/WarehousesPage';
import StockPage from '@/pages/StockPage';

// Placeholder components for pages not yet implemented
function AuditPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Audit Log</h1>
      <p className="text-muted-foreground">Audit log page coming soon...</p>
    </div>
  );
}

function ApiDocsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">API Documentation</h1>
      <p className="text-muted-foreground">
        Visit <a href="/docs" target="_blank" className="text-primary hover:underline">Swagger UI</a> or{' '}
        <a href="/redoc" target="_blank" className="text-primary hover:underline">ReDoc</a> for API documentation.
      </p>
    </div>
  );
}

export default function App() {
  const auth = useAuthProvider();

  return (
    <AuthContext.Provider value={auth}>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes with layout */}
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="warehouses" element={<WarehousesPage />} />
          <Route path="stock" element={<StockPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="api-docs" element={<ApiDocsPage />} />
        </Route>

        {/* Fallback for unknown routes */}
        <Route path="*" element={
          <div className="min-h-screen flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-4xl font-bold mb-4">404</h1>
              <p className="text-muted-foreground mb-4">Page not found</p>
              <a href="/" className="text-primary hover:underline">
                Go back to dashboard
              </a>
            </div>
          </div>
        } />
      </Routes>

      {/* Toast notifications */}
      <Toaster />
    </AuthContext.Provider>
  );
}