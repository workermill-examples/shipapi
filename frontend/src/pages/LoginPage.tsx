import { useState } from 'react';
import { Navigate, useLocation } from 'react-router';
import { Package, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();

  const [email, setEmail] = useState('demo@workermill.com');
  const [password, setPassword] = useState('demo1234');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = (location.state as { from?: string })?.from || '/dashboard';
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      toast.success('Successfully logged in!');
      // Navigation will happen automatically due to useAuth + ProtectedRoute
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const fillDemoCredentials = () => {
    setEmail('demo@workermill.com');
    setPassword('demo1234');
    toast.info('Demo credentials filled');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <Card>
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-6">
              <div className="flex items-center space-x-2">
                <Package className="h-8 w-8 text-primary" />
                <span className="text-2xl font-bold">ShipAPI</span>
              </div>
            </div>
            <CardTitle className="text-2xl text-center">Welcome back</CardTitle>
            <p className="text-center text-muted-foreground">
              Sign in to your ShipAPI dashboard
            </p>
          </CardHeader>

          <CardContent className="space-y-4">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isLoading}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    disabled={isLoading}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Signing in...
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>

            <Separator />

            <div className="space-y-3">
              <p className="text-sm text-center text-muted-foreground">
                Try the demo with these credentials:
              </p>
              <div className="bg-muted/50 rounded-lg p-3 space-y-1">
                <p className="text-sm font-mono">
                  <strong>Email:</strong> demo@workermill.com
                </p>
                <p className="text-sm font-mono">
                  <strong>Password:</strong> demo1234
                </p>
              </div>
              <Button
                variant="outline"
                className="w-full"
                onClick={fillDemoCredentials}
                disabled={isLoading}
              >
                Use Demo Credentials
              </Button>
            </div>
          </CardContent>

          <CardFooter>
            <div className="w-full text-center">
              <p className="text-xs text-muted-foreground">
                Built by{' '}
                <a
                  href="https://workermill.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  WorkerMill
                </a>
              </p>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}