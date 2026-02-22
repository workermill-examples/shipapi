const DEMO_EMAIL = "demo@workermill.com";
const DEMO_PASSWORD = "demo1234";
const DEMO_API_KEY = "sk_demo_shipapi_2026_showcase_key";

interface DemoAccessProps {
  dashboardUrl?: string;
  githubUrl?: string;
  className?: string;
}

export function DemoAccess({
  dashboardUrl = "https://taskpulse.workermill.com",
  githubUrl = "https://github.com/workermill-examples/taskpulse",
  className,
}: DemoAccessProps) {
  return (
    <section
      id="demo"
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50${className ? ` ${className}` : ""}`}
      aria-labelledby="demo-heading"
    >
      <div className="text-center mb-10">
        <h2 id="demo-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          Demo Access
        </h2>
        <p className="text-gray-500">
          Use these credentials to explore the full dashboard — pre-seeded with realistic data
        </p>
      </div>

      <div className="max-w-2xl mx-auto">
        {/* Credentials card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          {/* Email / Password / Role row */}
          <div className="px-6 py-5 border-b border-gray-800 grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Email</div>
              <code className="text-gray-200 text-xs">{DEMO_EMAIL}</code>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Password</div>
              <code className="text-gray-200 text-xs">{DEMO_PASSWORD}</code>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1.5">Role</div>
              <span
                className="inline-flex items-center gap-1 bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs px-2 py-0.5 rounded-full"
                role="status"
              >
                admin
              </span>
            </div>
          </div>

          {/* API key row */}
          <div className="px-6 py-5 border-b border-gray-800">
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">API Key</div>
            <div className="flex items-center gap-2">
              <code
                className="flex-1 bg-gray-800 rounded-lg px-3 py-2.5 text-xs text-green-400 break-all font-mono"
                aria-label="Demo API key"
              >
                {DEMO_API_KEY}
              </code>
            </div>
          </div>

          {/* Quick start */}
          <div className="px-6 py-5">
            <div className="text-xs text-gray-600 mb-3 uppercase tracking-wider">Quick start</div>
            <pre className="m-0 overflow-x-auto text-xs">
              <code className="text-gray-300 font-mono leading-relaxed">
                <span className="text-gray-500">$ </span>
                <span className="text-green-400">curl</span>
                {" https://taskpulse.workermill.com/api/tasks \\\n"}
                {"  "}
                <span className="text-blue-300">-H</span>
                {' "Authorization: Bearer '}
                <span className="text-amber-400">&lt;token&gt;</span>
                {'"'}
              </code>
            </pre>
          </div>
        </div>

        {/* CTA buttons */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <a
            href={dashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-3 rounded-xl transition-colors shadow-lg shadow-blue-900/30"
          >
            {/* External link icon */}
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            Open Dashboard →
          </a>
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium px-5 py-3 rounded-xl transition-colors border border-gray-700/50"
          >
            {/* GitHub icon */}
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            View Source
          </a>
        </div>
      </div>
    </section>
  );
}
