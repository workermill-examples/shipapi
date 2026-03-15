import { Routes, Route } from 'react-router';
import { AuthContext, useAuthProvider } from '@/hooks/useAuth';
import { Toaster } from '@/components/ui/sonner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Layout } from '@/components/Layout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { LoginPage } from '@/pages/LoginPage';
import LandingPage from '@/pages/LandingPage';
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
        {/* Public landing page route */}
        <Route path="/" element={<div className="animate-fade-in"><LandingPage /></div>} />

        {/* Public login route */}
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
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route
            index
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <DashboardPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="products"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <ProductsPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="categories"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <CategoriesPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="warehouses"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <WarehousesPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="stock"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <StockPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="audit"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <AuditPage />
                </div>
              </ErrorBoundary>
            }
          />
          <Route
            path="api-docs"
            element={
              <ErrorBoundary>
                <div className="animate-fade-in">
                  <ApiDocsPage />
                </div>
              </ErrorBoundary>
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
                <a href="/dashboard" className="text-primary hover:underline">
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