"""Showcase endpoints — public stats API and HTML landing page."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import AuditLog, Category, Product, StockLevel, StockTransfer, Warehouse
from src.schemas.showcase import ShowcaseStats

router = APIRouter(prefix="/showcase", tags=["Showcase"])
root_router = APIRouter()


@router.get(
    "/stats",
    response_model=ShowcaseStats,
    summary="Public showcase statistics",
    description="Returns aggregate counts for the showcase landing page. No authentication required.",
)
async def get_showcase_stats(db: AsyncSession = Depends(get_db)) -> ShowcaseStats:  # noqa: B008
    """Return aggregate counts across all core resources in a single SQL round-trip."""
    result = await db.execute(
        select(
            select(func.count())
            .where(Product.is_active.is_(True))
            .scalar_subquery()
            .label("products"),
            select(func.count()).select_from(Category).scalar_subquery().label("categories"),
            select(func.count())
            .where(Warehouse.is_active.is_(True))
            .scalar_subquery()
            .label("warehouses"),
            select(func.count())
            .where(StockLevel.quantity < StockLevel.min_threshold)
            .scalar_subquery()
            .label("stock_alerts"),
            select(func.count())
            .select_from(StockTransfer)
            .scalar_subquery()
            .label("stock_transfers"),
            select(func.count()).select_from(AuditLog).scalar_subquery().label("audit_log_entries"),
        )
    )
    row = result.one()
    return ShowcaseStats(
        products=row.products,
        categories=row.categories,
        warehouses=row.warehouses,
        stock_alerts=row.stock_alerts,
        stock_transfers=row.stock_transfers,
        audit_log_entries=row.audit_log_entries,
    )


_LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ShipAPI — Inventory Management API Built by AI</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link
    rel="stylesheet"
    href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css"
  />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
    body { font-family: 'Inter', sans-serif; }
    code, pre { font-family: 'JetBrains Mono', monospace; }
    .gradient-text {
      background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #34d399 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .stat-card { transition: transform 0.2s, box-shadow 0.2s; }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(96, 165, 250, 0.15); }
    .explorer-response { max-height: 400px; overflow-y: auto; }
    .badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500;
    }
    .endpoint-row { transition: background 0.15s; }
    .endpoint-row:hover { background: rgba(255,255,255,0.03); }
    .loading-pulse { animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .hljs { background: #0d1117 !important; border-radius: 8px; padding: 16px !important; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #1f2937; }
    ::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 3px; }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen">

<!-- ===== NAVIGATION ===== -->
<nav class="border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm">S</div>
      <span class="font-semibold text-white">ShipAPI</span>
      <span class="text-gray-600 hidden sm:inline">·</span>
      <a href="https://workermill.com" target="_blank" rel="noopener"
         class="hidden sm:flex items-center gap-1.5 text-sm text-gray-400 hover:text-gray-200 transition-colors">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        Built by WorkerMill
      </a>
    </div>
    <div class="flex items-center gap-2 sm:gap-3">
      <a href="/docs" class="text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5">Docs</a>
      <a href="/redoc" class="text-sm text-gray-400 hover:text-white transition-colors px-3 py-1.5">ReDoc</a>
      <a href="https://github.com/workermill-examples/shipapi" target="_blank" rel="noopener"
         class="flex items-center gap-1.5 text-sm bg-gray-800 hover:bg-gray-700 text-gray-200 px-3 py-1.5 rounded-lg transition-colors">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub
      </a>
    </div>
  </div>
</nav>

<!-- ===== HERO ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 pt-20 pb-16 text-center">
  <div class="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 mb-8">
    <div class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
    <span class="text-sm text-blue-300 font-medium">Live on Railway · Deployed by AI</span>
  </div>
  <h1 class="text-5xl sm:text-7xl font-extrabold tracking-tight mb-6">
    <span class="gradient-text">ShipAPI</span>
  </h1>
  <p class="text-xl sm:text-2xl text-gray-300 max-w-3xl mx-auto mb-4 leading-relaxed">
    A fully functional inventory management REST API —<br class="hidden sm:block" />
    written, tested, and deployed <strong class="text-white">entirely by AI workers</strong>.
  </p>
  <p class="text-gray-500 mb-10 max-w-2xl mx-auto">
    50 products, 20 categories, 3 warehouses, JWT + API key auth, audit trail, rate limiting,
    stock alerts — all built by <a href="https://workermill.com" target="_blank" rel="noopener" class="text-blue-400 hover:underline">WorkerMill</a> AI agents across 5 epics and 30 stories.
  </p>
  <div class="flex flex-wrap items-center justify-center gap-3">
    <a href="/docs" class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-3 rounded-xl transition-colors">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      Swagger UI
    </a>
    <a href="/redoc" class="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium px-6 py-3 rounded-xl transition-colors">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      ReDoc
    </a>
    <a href="https://github.com/workermill-examples/shipapi" target="_blank" rel="noopener"
       class="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium px-6 py-3 rounded-xl transition-colors">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
      View Source
    </a>
  </div>
</section>

<!-- ===== LIVE STATS ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16">
  <div class="text-center mb-10">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">Live Stats</h2>
    <p class="text-gray-500 text-sm">Fetched in real-time from <code class="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300">/api/v1/showcase/stats</code></p>
  </div>
  <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4" id="stats-grid">
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-blue-400 loading-pulse" id="stat-products">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Products</div>
    </div>
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-purple-400 loading-pulse" id="stat-categories">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Categories</div>
    </div>
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-emerald-400 loading-pulse" id="stat-warehouses">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Warehouses</div>
    </div>
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-amber-400 loading-pulse" id="stat-alerts">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Stock Alerts</div>
    </div>
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-cyan-400 loading-pulse" id="stat-transfers">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Transfers</div>
    </div>
    <div class="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-3xl font-bold text-rose-400 loading-pulse" id="stat-audit">—</div>
      <div class="text-xs text-gray-500 mt-1.5 uppercase tracking-wider">Audit Entries</div>
    </div>
  </div>
</section>

<!-- ===== TECH STACK ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50">
  <div class="text-center mb-10">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">Tech Stack</h2>
    <p class="text-gray-500">Production-grade Python API, chosen and implemented by AI workers</p>
  </div>
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto">
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center hover:border-gray-700 transition-colors">
      <div class="text-3xl mb-3">⚡</div>
      <div class="font-semibold text-white text-sm">FastAPI</div>
      <div class="text-xs text-gray-500 mt-1">Async REST</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center hover:border-gray-700 transition-colors">
      <div class="text-3xl mb-3">🗄️</div>
      <div class="font-semibold text-white text-sm">SQLAlchemy 2</div>
      <div class="text-xs text-gray-500 mt-1">Async ORM</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center hover:border-gray-700 transition-colors">
      <div class="text-3xl mb-3">🐘</div>
      <div class="font-semibold text-white text-sm">PostgreSQL</div>
      <div class="text-xs text-gray-500 mt-1">Neon Serverless</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center hover:border-gray-700 transition-colors">
      <div class="text-3xl mb-3">🐍</div>
      <div class="font-semibold text-white text-sm">Python 3.13</div>
      <div class="text-xs text-gray-500 mt-1">Latest syntax</div>
    </div>
  </div>
</section>

<!-- ===== INTERACTIVE EXPLORER ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50">
  <div class="text-center mb-10">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">Interactive API Explorer</h2>
    <p class="text-gray-500">Pre-authenticated with the demo API key — try real endpoints live</p>
  </div>

  <div class="grid lg:grid-cols-2 gap-6">
    <!-- Endpoints list -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div class="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <span class="font-medium text-sm text-gray-300">Endpoints</span>
        <div class="badge bg-green-500/10 border border-green-500/20 text-green-400">
          <div class="w-1.5 h-1.5 rounded-full bg-green-400"></div>
          Live
        </div>
      </div>
      <div class="divide-y divide-gray-800/50">
        <div class="endpoint-row px-5 py-4 cursor-pointer" onclick="tryEndpoint('products')">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="badge bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs">GET</span>
              <code class="text-sm text-gray-200">/api/v1/products</code>
            </div>
            <button class="text-xs text-gray-500 hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); copyCommand('products')">copy curl</button>
          </div>
          <p class="text-xs text-gray-500">List all active products with pagination</p>
        </div>
        <div class="endpoint-row px-5 py-4 cursor-pointer" onclick="tryEndpoint('categories')">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="badge bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs">GET</span>
              <code class="text-sm text-gray-200">/api/v1/categories</code>
            </div>
            <button class="text-xs text-gray-500 hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); copyCommand('categories')">copy curl</button>
          </div>
          <p class="text-xs text-gray-500">List product categories with hierarchy</p>
        </div>
        <div class="endpoint-row px-5 py-4 cursor-pointer" onclick="tryEndpoint('warehouses')">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="badge bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs">GET</span>
              <code class="text-sm text-gray-200">/api/v1/warehouses</code>
            </div>
            <button class="text-xs text-gray-500 hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); copyCommand('warehouses')">copy curl</button>
          </div>
          <p class="text-xs text-gray-500">List warehouses with stock summaries</p>
        </div>
        <div class="endpoint-row px-5 py-4 cursor-pointer" onclick="tryEndpoint('alerts')">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="badge bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs">GET</span>
              <code class="text-sm text-gray-200">/api/v1/stock/alerts</code>
            </div>
            <button class="text-xs text-gray-500 hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); copyCommand('alerts')">copy curl</button>
          </div>
          <p class="text-xs text-gray-500">Products below minimum stock threshold</p>
        </div>
        <div class="endpoint-row px-5 py-4 cursor-pointer" onclick="tryEndpoint('health')">
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <span class="badge bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs">GET</span>
              <code class="text-sm text-gray-200">/api/v1/health</code>
            </div>
            <button class="text-xs text-gray-500 hover:text-blue-400 transition-colors" onclick="event.stopPropagation(); copyCommand('health')">copy curl</button>
          </div>
          <p class="text-xs text-gray-500">Service health and database status</p>
        </div>
      </div>
    </div>

    <!-- Response panel -->
    <div class="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col">
      <div class="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <span class="font-medium text-sm text-gray-300" id="response-title">Click an endpoint to try it</span>
        <div class="flex items-center gap-2">
          <span id="response-status" class="text-xs font-mono"></span>
          <span id="response-time" class="text-xs text-gray-600"></span>
        </div>
      </div>
      <div class="flex-1 p-4 explorer-response">
        <pre id="response-body" class="text-sm text-gray-500 italic">
// Response will appear here</pre>
      </div>
    </div>
  </div>
</section>

<!-- ===== BUILD HISTORY ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50">
  <div class="text-center mb-12">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">How It Was Built</h2>
    <p class="text-gray-500">5 epics · 30 stories · 344 tests · zero human-written lines of code</p>
  </div>
  <div class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400 text-sm font-bold">1</div>
        <div>
          <div class="font-semibold text-white text-sm">Core Foundation</div>
          <div class="text-xs text-gray-500">Epic SA-1 · 6 stories</div>
        </div>
      </div>
      <p class="text-sm text-gray-400">Database setup, async SQLAlchemy, Alembic migrations, pydantic-settings config, health endpoint, CORS &amp; middleware stack, Railway CI/CD pipeline.</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-400 text-sm font-bold">2</div>
        <div>
          <div class="font-semibold text-white text-sm">Authentication</div>
          <div class="text-xs text-gray-500">Epic SA-2 · 6 stories</div>
        </div>
      </div>
      <p class="text-sm text-gray-400">JWT access &amp; refresh tokens, API key auth (SHA-256 hashed), bcrypt password hashing, role-based access control (user/admin), rate limiting.</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 text-sm font-bold">3</div>
        <div>
          <div class="font-semibold text-white text-sm">Product Catalog</div>
          <div class="text-xs text-gray-500">Epic SA-3 · 6 stories</div>
        </div>
      </div>
      <p class="text-sm text-gray-400">Category hierarchy with parent/child, product CRUD with soft delete, full-text search via PostgreSQL tsvector &amp; GIN index, price &amp; category filters.</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400 text-sm font-bold">4</div>
        <div>
          <div class="font-semibold text-white text-sm">Inventory Operations</div>
          <div class="text-xs text-gray-500">Epic SA-4 · 6 stories</div>
        </div>
      </div>
      <p class="text-sm text-gray-400">Warehouse management, stock levels with min-threshold alerts, atomic stock transfers with <code class="text-amber-300 text-xs">SELECT FOR UPDATE</code> locking, full audit trail.</p>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-6 hover:border-gray-700 transition-colors">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 text-sm font-bold">5</div>
        <div>
          <div class="font-semibold text-white text-sm">Showcase &amp; Demo</div>
          <div class="text-xs text-gray-500">Epic SA-5 · 6 stories</div>
        </div>
      </div>
      <p class="text-sm text-gray-400">Seed data (50 products, 20 categories, 3 warehouses), demo API key, this landing page &amp; interactive explorer, public stats endpoint.</p>
    </div>
    <div class="bg-gray-900 border border-blue-500/20 rounded-xl p-6">
      <div class="text-center py-4">
        <div class="text-4xl font-extrabold text-white mb-1">344</div>
        <div class="text-sm text-gray-400 mb-3">Tests passing</div>
        <div class="text-xs text-gray-600">Every test written and run by AI workers<br/>across unit, integration, and E2E suites</div>
      </div>
    </div>
  </div>
  <div class="mt-8 text-center">
    <a href="https://workermill.com" target="_blank" rel="noopener"
       class="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
      Learn how WorkerMill builds software with AI workers →
    </a>
  </div>
</section>

<!-- ===== CODE QUALITY ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50">
  <div class="text-center mb-10">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">Code Quality</h2>
    <p class="text-gray-500">Production standards enforced from day one</p>
  </div>
  <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto">
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-2xl mb-2">✅</div>
      <div class="font-semibold text-white text-sm mb-1">344 Tests</div>
      <div class="text-xs text-gray-500">pytest · ≥80% coverage</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-2xl mb-2">🔍</div>
      <div class="font-semibold text-white text-sm mb-1">mypy Strict</div>
      <div class="text-xs text-gray-500">Full type annotations</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-2xl mb-2">⚡</div>
      <div class="font-semibold text-white text-sm mb-1">ruff</div>
      <div class="text-xs text-gray-500">Linting &amp; formatting</div>
    </div>
    <div class="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center">
      <div class="text-2xl mb-2">🚀</div>
      <div class="font-semibold text-white text-sm mb-1">CI/CD</div>
      <div class="text-xs text-gray-500">GitHub Actions · Railway</div>
    </div>
  </div>
</section>

<!-- ===== DEMO ACCESS ===== -->
<section class="max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50">
  <div class="text-center mb-10">
    <h2 class="text-2xl sm:text-3xl font-bold text-white mb-2">Demo Access</h2>
    <p class="text-gray-500">Use these credentials to explore the full API</p>
  </div>
  <div class="max-w-2xl mx-auto bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
    <div class="px-6 py-5 border-b border-gray-800 grid grid-cols-3 gap-4 text-sm">
      <div>
        <div class="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Email</div>
        <code class="text-gray-200 text-xs">demo@workermill.com</code>
      </div>
      <div>
        <div class="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Password</div>
        <code class="text-gray-200 text-xs">demo1234</code>
      </div>
      <div>
        <div class="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Role</div>
        <span class="badge bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs">admin</span>
      </div>
    </div>
    <div class="px-6 py-5">
      <div class="text-xs text-gray-500 uppercase tracking-wider mb-2">API Key</div>
      <div class="flex items-center gap-2">
        <code class="flex-1 bg-gray-800 rounded-lg px-3 py-2 text-xs text-green-400 break-all" id="api-key-display">sk_demo_shipapi_2026_showcase_key</code>
        <button onclick="copyApiKey()" class="flex-shrink-0 text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-3 py-2 rounded-lg transition-colors" id="copy-key-btn">Copy</button>
      </div>
    </div>
    <div class="px-6 pb-5">
      <div class="text-xs text-gray-600 mb-3">Quick start with curl:</div>
      <pre class="bg-gray-800/80 rounded-lg p-3 text-xs overflow-x-auto"><code class="language-bash">curl https://shipapi.workermill.com/api/v1/products \
  -H "X-API-Key: sk_demo_shipapi_2026_showcase_key"</code></pre>
    </div>
  </div>
  <div class="mt-6 text-center flex flex-wrap items-center justify-center gap-4">
    <a href="/docs" class="inline-flex items-center gap-2 text-sm bg-gray-800 hover:bg-gray-700 text-gray-200 px-5 py-2.5 rounded-xl transition-colors">
      Open Swagger UI →
    </a>
    <a href="/redoc" class="inline-flex items-center gap-2 text-sm bg-gray-800 hover:bg-gray-700 text-gray-200 px-5 py-2.5 rounded-xl transition-colors">
      Open ReDoc →
    </a>
  </div>
</section>

<!-- ===== FOOTER ===== -->
<footer class="border-t border-gray-800/50 mt-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <div class="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs">S</div>
      <span class="text-gray-500 text-sm">ShipAPI — built by <a href="https://workermill.com" target="_blank" rel="noopener" class="text-gray-400 hover:text-white transition-colors">WorkerMill</a> AI workers</span>
    </div>
    <div class="flex items-center gap-4 text-sm">
      <a href="/api/v1/health" class="text-gray-600 hover:text-gray-400 transition-colors">Health</a>
      <a href="/docs" class="text-gray-600 hover:text-gray-400 transition-colors">Docs</a>
      <a href="/redoc" class="text-gray-600 hover:text-gray-400 transition-colors">ReDoc</a>
      <a href="https://github.com/workermill-examples/shipapi" target="_blank" rel="noopener" class="text-gray-600 hover:text-gray-400 transition-colors">GitHub</a>
    </div>
  </div>
</footer>

<script>
const DEMO_API_KEY = 'sk_demo_shipapi_2026_showcase_key';

const ENDPOINTS = {
  products:    { path: '/api/v1/products',      auth: true,  label: 'GET /api/v1/products' },
  categories:  { path: '/api/v1/categories',    auth: false, label: 'GET /api/v1/categories' },
  warehouses:  { path: '/api/v1/warehouses',    auth: true,  label: 'GET /api/v1/warehouses' },
  alerts:      { path: '/api/v1/stock/alerts',  auth: true,  label: 'GET /api/v1/stock/alerts' },
  health:      { path: '/api/v1/health',        auth: false, label: 'GET /api/v1/health' },
};

// Fetch and populate live stats
async function loadStats() {
  try {
    const res = await fetch('/api/v1/showcase/stats');
    if (!res.ok) return;
    const data = await res.json();
    const ids = ['products','categories','warehouses','alerts','transfers','audit'];
    const keys = ['products','categories','warehouses','stock_alerts','stock_transfers','audit_log_entries'];
    ids.forEach((id, i) => {
      const el = document.getElementById('stat-' + id);
      if (el) {
        el.classList.remove('loading-pulse');
        el.textContent = data[keys[i]].toLocaleString();
      }
    });
  } catch (e) {
    // silently fail — stat cards stay as "—"
  }
}

// Try a live endpoint
async function tryEndpoint(key) {
  const ep = ENDPOINTS[key];
  if (!ep) return;

  const titleEl = document.getElementById('response-title');
  const bodyEl = document.getElementById('response-body');
  const statusEl = document.getElementById('response-status');
  const timeEl = document.getElementById('response-time');

  titleEl.textContent = ep.label;
  bodyEl.className = 'text-sm text-gray-400 italic';
  bodyEl.innerHTML = '// Loading...';
  statusEl.textContent = '';
  timeEl.textContent = '';

  const headers = {};
  if (ep.auth) headers['X-API-Key'] = DEMO_API_KEY;

  const start = performance.now();
  try {
    const res = await fetch(ep.path, { headers });
    const ms = Math.round(performance.now() - start);
    const json = await res.json();
    const formatted = JSON.stringify(json, null, 2);

    timeEl.textContent = ms + 'ms';
    statusEl.textContent = res.status + ' ' + res.statusText;
    statusEl.className = res.ok
      ? 'text-xs font-mono text-green-400'
      : 'text-xs font-mono text-red-400';

    bodyEl.className = 'text-sm';
    bodyEl.innerHTML = '<code class="language-json">' + formatted.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</code>';
    hljs.highlightElement(bodyEl.querySelector('code'));
  } catch (e) {
    bodyEl.className = 'text-sm text-red-400 italic';
    bodyEl.innerHTML = '// Error: ' + e.message;
  }
}

// Copy curl command
function copyCommand(key) {
  const ep = ENDPOINTS[key];
  if (!ep) return;
  const base = window.location.origin;
  let cmd = 'curl ' + base + ep.path;
  if (ep.auth) cmd += ' \\\n  -H "X-API-Key: ' + DEMO_API_KEY + '"';
  navigator.clipboard.writeText(cmd).then(() => {
    // brief visual feedback via title bar
    const titleEl = document.getElementById('response-title');
    const prev = titleEl.textContent;
    titleEl.textContent = 'Copied!';
    setTimeout(() => { titleEl.textContent = prev; }, 1500);
  }).catch(() => {});
}

// Copy API key
function copyApiKey() {
  const btn = document.getElementById('copy-key-btn');
  navigator.clipboard.writeText(DEMO_API_KEY).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
  }).catch(() => {});
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  hljs.highlightAll();
});
</script>
</body>
</html>"""


@root_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page() -> str:
    """Serve the ShipAPI showcase landing page."""
    return _LANDING_HTML
