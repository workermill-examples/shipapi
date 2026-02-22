interface QualityItem {
  emoji: string;
  label: string;
  subtitle: string;
}

const QUALITY_ITEMS: QualityItem[] = [
  { emoji: "✅", label: "140 Tests", subtitle: "74 unit · 66 E2E" },
  { emoji: "🔷", label: "TypeScript Strict", subtitle: "Full type safety" },
  { emoji: "⚡", label: "ESLint Clean", subtitle: "Zero warnings" },
  { emoji: "🚀", label: "CI/CD", subtitle: "GitHub Actions · Vercel" },
];

interface CodeQualityProps {
  githubUrl?: string;
  className?: string;
}

export function CodeQuality({
  githubUrl = "https://github.com/workermill-examples/taskpulse",
  className,
}: CodeQualityProps) {
  return (
    <section
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50${className ? ` ${className}` : ""}`}
      aria-labelledby="quality-heading"
    >
      <div className="text-center mb-10">
        <h2 id="quality-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          Code Quality
        </h2>
        <p className="text-gray-500">
          Production standards enforced from day one, by AI workers
        </p>
      </div>

      {/* Quality metric cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-4xl mx-auto">
        {QUALITY_ITEMS.map((item) => (
          <div
            key={item.label}
            className="bg-gray-900 border border-gray-800 rounded-xl p-5 text-center hover:border-gray-700 transition-colors"
          >
            <div className="text-2xl mb-2" aria-hidden="true">
              {item.emoji}
            </div>
            <div className="font-semibold text-white text-sm mb-1">{item.label}</div>
            <div className="text-xs text-gray-500">{item.subtitle}</div>
          </div>
        ))}
      </div>

      {/* Test breakdown detail */}
      <div className="mt-6 max-w-4xl mx-auto grid sm:grid-cols-3 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0"
            aria-hidden="true"
          >
            {/* Beaker / test icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#60a5fa"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v11l-4 7h14l-4-7V3" />
            </svg>
          </div>
          <div>
            <div className="font-semibold text-white text-sm">74 Unit Tests</div>
            <div className="text-xs text-gray-500 mt-0.5">Jest · component &amp; logic coverage</div>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0"
            aria-hidden="true"
          >
            {/* Globe / E2E icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#34d399"
              strokeWidth="2"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 010 20M12 2a15.3 15.3 0 000 20" />
            </svg>
          </div>
          <div>
            <div className="font-semibold text-white text-sm">66 E2E Tests</div>
            <div className="text-xs text-gray-500 mt-0.5">Playwright · full user flows</div>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center flex-shrink-0"
            aria-hidden="true"
          >
            {/* Shield / CI icon */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#a78bfa"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div>
            <div className="font-semibold text-white text-sm">CI Enforced</div>
            <div className="text-xs text-gray-500 mt-0.5">All checks run on every push</div>
          </div>
        </div>
      </div>

      {/* Quick start code block */}
      <div className="mt-6 max-w-2xl mx-auto bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs text-gray-500 uppercase tracking-wider">Run the test suite</div>
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" aria-hidden="true" />
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" aria-hidden="true" />
            <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" aria-hidden="true" />
          </div>
        </div>
        <pre className="text-xs overflow-x-auto m-0">
          <code className="text-gray-300 font-mono leading-relaxed">
            <span className="text-gray-500">$ </span>
            <span className="text-green-400">git clone</span>
            {" "}
            <span className="text-blue-300">{githubUrl}</span>
            {"\n"}
            <span className="text-gray-500">$ </span>
            <span className="text-green-400">npm install</span>
            {"\n"}
            <span className="text-gray-500">$ </span>
            <span className="text-green-400">npm test</span>
            {"           "}
            <span className="text-gray-600"># 74 unit tests</span>
            {"\n"}
            <span className="text-gray-500">$ </span>
            <span className="text-green-400">npx playwright test</span>
            {"  "}
            <span className="text-gray-600"># 66 E2E tests</span>
          </code>
        </pre>
      </div>
    </section>
  );
}
