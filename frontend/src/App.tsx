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
import AuditPage from '@/pages/AuditPage';
import ApiDocsPage from '@/pages/ApiDocsPage';

export default function App() {
  const auth = useAuthProvider();

  return (
    <AuthContext.Provider value={auth}>
      <Routes>
        {/* Public route */}
        <Route
          path="/login"
          element={
            <div className="animate-fade-in">
              <LoginPage />
            </div>
          }
        />

        {/* Protected routes with layout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <div className="animate-fade-in">
                <DashboardPage />
              </div>
            }
          />
          <Route
            path="products"
            element={
              <div className="animate-fade-in">
                <ProductsPage />
              </div>
            }
          />
          <Route
            path="categories"
            element={
              <div className="animate-fade-in">
                <CategoriesPage />
              </div>
            }
          />
          <Route
            path="warehouses"
            element={
              <div className="animate-fade-in">
                <WarehousesPage />
              </div>
            }
          />
          <Route
            path="stock"
            element={
              <div className="animate-fade-in">
                <StockPage />
              </div>
            }
          />
          <Route
            path="audit"
            element={
              <div className="animate-fade-in">
                <AuditPage />
              </div>
            }
          />
          <Route
            path="api-docs"
            element={
              <div className="animate-fade-in">
                <ApiDocsPage />
              </div>
            }
          />
        </Route>

        {/* Fallback for unknown routes */}
        <Route
          path="*"
          element={
            <div className="min-h-screen flex items-center justify-center animate-fade-in">
              <div className="text-center animate-slide-in-from-bottom">
                <h1 className="text-4xl font-bold mb-4">404</h1>
                <p className="text-muted-foreground mb-4">Page not found</p>
                <a href="/" className="text-primary hover:underline">
                  Go back to dashboard
                </a>
              </div>
            </div>
          }
        />
      </Routes>

      {/* Toast notifications */}
      <Toaster />
    </AuthContext.Provider>
  );
}