interface EndpointItem {
  method: string;
  path: string;
  description: string;
  methodColor: string;
}

const PREVIEW_ENDPOINTS: EndpointItem[] = [
  {
    method: "GET",
    path: "/api/v1/products",
    description: "List all active products with pagination",
    methodColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    method: "GET",
    path: "/api/v1/categories",
    description: "List product categories with hierarchy",
    methodColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    method: "GET",
    path: "/api/v1/warehouses",
    description: "List warehouses with stock summaries",
    methodColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    method: "GET",
    path: "/api/v1/stock/alerts",
    description: "Products below minimum stock threshold",
    methodColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    method: "GET",
    path: "/api/v1/health",
    description: "Service health check and database status",
    methodColor: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
];

const SAMPLE_RESPONSE = `{
  "items": [
    {
      "id": "a1b2c3d4-...",
      "sku": "LAPTOP-PRO-15",
      "name": "Laptop Pro 15\"",
      "price": 1299.99,
      "category": "Electronics",
      "stock_quantity": 42
    },
    {
      "id": "e5f6g7h8-...",
      "sku": "WIRELESS-MOUSE",
      "name": "Wireless Mouse",
      "price": 49.99,
      "category": "Accessories",
      "stock_quantity": 150
    }
  ],
  "total": 50,
  "page": 1,
  "size": 20,
  "pages": 3
}`;

interface DashboardPreviewProps {
  explorerUrl?: string;
  docsUrl?: string;
  className?: string;
}

export function DashboardPreview({
  explorerUrl = "#explorer",
  docsUrl = "/docs",
  className,
}: DashboardPreviewProps) {
  return (
    <section
      id="explorer-preview"
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50${className ? ` ${className}` : ""}`}
      aria-labelledby="preview-heading"
    >
      <div className="text-center mb-10">
        <h2 id="preview-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          Interactive API Explorer
        </h2>
        <p className="text-gray-500">
          Pre-authenticated with the demo API key — make real calls to live endpoints
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Endpoint list panel */}
        <div
          className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
          role="region"
          aria-label="Available API endpoints"
        >
          {/* Panel header */}
          <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
            <span className="font-medium text-sm text-gray-300">Endpoints</span>
            <div
              className="inline-flex items-center gap-1.5 bg-green-500/10 border border-green-500/20 text-green-400 text-xs px-3 py-1 rounded-full"
              role="status"
            >
              <div
                className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"
                aria-hidden="true"
              />
              Live
            </div>
          </div>

          {/* Endpoint rows */}
          <div className="divide-y divide-gray-800/60" role="list">
            {PREVIEW_ENDPOINTS.map((ep, idx) => (
              <div
                key={ep.path}
                className={`px-5 py-4${idx === 0 ? " bg-blue-500/[0.04] border-l-2 border-blue-500" : ""}`}
                role="listitem"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-semibold ${ep.methodColor}`}
                    >
                      {ep.method}
                    </span>
                    <code className="text-sm text-gray-200">{ep.path}</code>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{ep.description}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Response preview panel */}
        <div
          className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden flex flex-col"
          role="region"
          aria-label="Sample API response"
        >
          {/* Panel header */}
          <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
            <span className="font-medium text-sm text-gray-300 truncate">
              GET /api/v1/products
            </span>
            <div className="flex items-center gap-2 flex-shrink-0 ml-2">
              <span className="text-xs font-mono text-green-400">200 OK</span>
              <span className="text-xs text-gray-600">42ms</span>
            </div>
          </div>

          {/* Sample JSON response */}
          <div className="flex-1 p-4 overflow-auto max-h-72">
            <pre className="text-xs m-0 leading-relaxed">
              <code className="text-gray-300 font-mono">
                {SAMPLE_RESPONSE.split("\n").map((line, i) => {
                  const trimmed = line.trimStart();
                  const indent = line.length - trimmed.length;

                  // Key coloring: "key": value
                  const keyMatch = trimmed.match(/^("[\w\s]+"):\s(.*)$/);
                  if (keyMatch) {
                    const [, key, rest] = keyMatch;
                    const valueClass = /^[\d.]+/.test(rest)
                      ? "text-amber-400"
                      : rest.startsWith('"')
                        ? "text-green-400"
                        : "text-blue-400";

                    return (
                      <span key={i}>
                        {" ".repeat(indent)}
                        <span className="text-blue-300">{key}</span>
                        <span className="text-gray-500">: </span>
                        <span className={valueClass}>{rest}</span>
                        {"\n"}
                      </span>
                    );
                  }

                  // Punctuation / structure lines
                  return (
                    <span key={i} className="text-gray-500">
                      {line}
                      {"\n"}
                    </span>
                  );
                })}
              </code>
            </pre>
          </div>

          {/* CTA overlay */}
          <div className="px-5 py-4 border-t border-gray-800 bg-gray-900/80 flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-gray-500">
              Try it live with the demo API key
            </span>
            <div className="flex items-center gap-2">
              <a
                href={explorerUrl}
                className="inline-flex items-center gap-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white font-medium px-4 py-2 rounded-lg transition-colors shadow-lg shadow-blue-900/30"
              >
                {/* Lightning / play icon */}
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                Try Explorer →
              </a>
              <a
                href={docsUrl}
                className="inline-flex items-center gap-1.5 text-sm bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium px-4 py-2 rounded-lg transition-colors border border-gray-700/50"
              >
                {/* Doc icon */}
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
                Swagger UI
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
