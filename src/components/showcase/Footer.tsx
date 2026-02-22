interface FooterProps {
  githubUrl?: string;
}

export function Footer({
  githubUrl = "https://github.com/workermill-examples/taskpulse",
}: FooterProps) {
  return (
    <footer className="border-t border-gray-800/50 mt-8" role="contentinfo">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Brand attribution */}
        <div className="flex items-center gap-3">
          <div
            className="w-7 h-7 rounded-md bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xs"
            aria-hidden="true"
          >
            T
          </div>
          <span className="text-gray-500 text-sm">
            TaskPulse — built by{" "}
            <a
              href="https://workermill.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-white transition-colors"
            >
              WorkerMill
            </a>{" "}
            AI workers
          </span>
        </div>

        {/* Footer navigation */}
        <nav className="flex items-center gap-4 text-sm" aria-label="Footer navigation">
          <a
            href="/api/v1/health"
            className="text-gray-600 hover:text-gray-400 transition-colors"
          >
            Health
          </a>
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-600 hover:text-gray-400 transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://workermill.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-600 hover:text-gray-400 transition-colors"
          >
            WorkerMill
          </a>
        </nav>
      </div>
    </footer>
  );
}
