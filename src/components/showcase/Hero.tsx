interface HeroProps {
  demoUrl?: string;
  githubUrl?: string;
}

export function Hero({
  demoUrl = "#demo",
  githubUrl = "https://github.com/workermill-examples/taskpulse",
}: HeroProps) {
  return (
    <header className="max-w-7xl mx-auto px-4 sm:px-6 pt-20 pb-16 text-center">
      {/* Live badge */}
      <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-1.5 mb-8">
        <div
          className="w-2 h-2 rounded-full bg-green-400 animate-pulse"
          aria-hidden="true"
        />
        <span className="text-sm text-blue-300 font-medium">
          Live on Vercel · Deployed by AI Workers
        </span>
      </div>

      {/* Gradient title */}
      <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight mb-6 leading-none">
        <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-emerald-400 bg-clip-text text-transparent">
          TaskPulse
        </span>
      </h1>

      {/* Subtitle */}
      <p className="text-xl sm:text-2xl text-gray-300 max-w-3xl mx-auto mb-4 leading-relaxed">
        A real-time background task monitoring dashboard —
        <br className="hidden sm:block" />
        written, tested, and deployed{" "}
        <strong className="text-white">entirely by AI workers</strong>.
      </p>

      {/* Feature highlights */}
      <p className="text-gray-500 mb-10 max-w-2xl mx-auto leading-relaxed">
        Task registry · Cron scheduling · Real-time traces · Log streaming · API
        key management · Global search · Keyboard shortcuts — all built by{" "}
        <a
          href="https://workermill.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 transition-colors underline decoration-blue-400/40 hover:decoration-blue-300/60"
        >
          WorkerMill
        </a>{" "}
        AI agents across 5 epics and 36 stories.
      </p>

      {/* CTA buttons */}
      <div
        className="flex flex-wrap items-center justify-center gap-3"
        role="navigation"
        aria-label="Quick links"
      >
        <a
          href={demoUrl}
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium px-6 py-3 rounded-xl transition-colors shadow-lg shadow-blue-900/30"
        >
          {/* Play icon */}
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none" />
          </svg>
          Try Demo
        </a>
        <a
          href={githubUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-gray-200 font-medium px-6 py-3 rounded-xl transition-colors border border-gray-700/50"
        >
          {/* GitHub icon */}
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
          </svg>
          View Source
        </a>
      </div>
    </header>
  );
}
