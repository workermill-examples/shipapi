import { Outlet } from 'react-router';
import { Sidebar } from './Sidebar';

export function Layout() {
  return (
    <div className="min-h-screen bg-background">
      <div className="flex h-screen">
        {/* Sidebar */}
        <aside className="w-64 shrink-0">
          <Sidebar />
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Header */}
          <header className="border-b border-border bg-card">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center space-x-4">
                <h1 className="text-xl font-semibold">ShipAPI Dashboard</h1>
              </div>

              {/* Header could include breadcrumbs, search, notifications etc. */}
              <div className="flex items-center space-x-4">
                <span className="text-sm text-muted-foreground">
                  Inventory Management System
                </span>
              </div>
            </div>
          </header>

          {/* Page Content */}
          <div className="flex-1 overflow-auto">
            <div className="p-6">
              <Outlet />
            </div>
          </div>

          {/* Footer */}
          <footer className="border-t border-border bg-card">
            <div className="px-6 py-4">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <div className="flex items-center space-x-4">
                  <span>&copy; 2025 ShipAPI</span>
                </div>
                <div className="flex items-center space-x-4">
                  <a
                    href="https://workermill.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    Built by WorkerMill
                  </a>
                </div>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}