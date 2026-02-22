interface Epic {
  number: number;
  title: string;
  subtitle: string;
  description: string;
  color: {
    badge: string;
    border: string;
    text: string;
  };
}

const EPICS: Epic[] = [
  {
    number: 1,
    title: "Project Setup & Dev Environment",
    subtitle: "Epic TP-1 · 7 stories",
    description:
      "Next.js 16 bootstrap, TypeScript strict config, ESLint, Prisma 7 schema, database migrations, CI pipeline setup, and Vercel project configuration.",
    color: {
      badge: "bg-blue-500/15 border-blue-500/25 text-blue-400",
      border: "hover:border-blue-500/30",
      text: "text-blue-400",
    },
  },
  {
    number: 2,
    title: "Core API & Task Engine",
    subtitle: "Epic TP-2 · 8 stories",
    description:
      "Task registry, job runner integration, run lifecycle management, REST API endpoints, background worker infrastructure, and authentication middleware.",
    color: {
      badge: "bg-purple-500/15 border-purple-500/25 text-purple-400",
      border: "hover:border-purple-500/30",
      text: "text-purple-400",
    },
  },
  {
    number: 3,
    title: "Dashboard UI",
    subtitle: "Epic TP-3 · 8 stories",
    description:
      "Real-time task monitoring dashboard, status cards, run history table, live log streaming, WebSocket integration, and responsive layout.",
    color: {
      badge: "bg-emerald-500/15 border-emerald-500/25 text-emerald-400",
      border: "hover:border-emerald-500/30",
      text: "text-emerald-400",
    },
  },
  {
    number: 4,
    title: "Scheduling, API Keys & Polish",
    subtitle: "Epic TP-4 · 7 stories",
    description:
      "Cron scheduling UI, API key management, global search with keyboard shortcuts, dark theme polish, mobile responsiveness, and accessibility improvements.",
    color: {
      badge: "bg-amber-500/15 border-amber-500/25 text-amber-400",
      border: "hover:border-amber-500/30",
      text: "text-amber-400",
    },
  },
  {
    number: 5,
    title: "Production Deploy & Validation",
    subtitle: "Epic TP-5 · 6 stories",
    description:
      "Vercel deployment, environment configuration, E2E test suite with Playwright, performance validation, seed data, and this showcase landing page.",
    color: {
      badge: "bg-rose-500/15 border-rose-500/25 text-rose-400",
      border: "hover:border-rose-500/30",
      text: "text-rose-400",
    },
  },
];

interface HowItWasBuiltProps {
  className?: string;
}

export function HowItWasBuilt({ className }: HowItWasBuiltProps) {
  return (
    <section
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50${className ? ` ${className}` : ""}`}
      aria-labelledby="build-heading"
    >
      <div className="text-center mb-12">
        <h2 id="build-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          How It Was Built
        </h2>
        <p className="text-gray-500">
          5 epics · 36 stories · 140 tests · zero human-written lines of code
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {EPICS.map((epic) => (
          <article
            key={epic.number}
            className={`bg-gray-900 border border-gray-800 ${epic.color.border} rounded-xl p-6 transition-all duration-200 hover:-translate-y-px`}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className={`w-8 h-8 rounded-lg ${epic.color.badge} border flex items-center justify-center text-sm font-bold`}
                aria-hidden="true"
              >
                {epic.number}
              </div>
              <div>
                <div className="font-semibold text-white text-sm">{epic.title}</div>
                <div className="text-xs text-gray-500">{epic.subtitle}</div>
              </div>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">{epic.description}</p>
          </article>
        ))}

        {/* Summary card */}
        <div
          className="bg-gray-900 border border-blue-500/20 rounded-xl p-6 flex flex-col items-center justify-center text-center"
          aria-label="Test count: 140 passing"
        >
          <div className="text-5xl font-extrabold text-white mb-1 tabular-nums">140</div>
          <div className="text-sm text-gray-400 mb-3">Tests passing</div>
          <div className="text-xs text-gray-600 leading-relaxed">
            74 unit tests + 66 E2E tests — written,
            <br />
            run, and maintained entirely by
            <br />
            WorkerMill AI workers
          </div>
        </div>
      </div>

      <div className="mt-10 text-center">
        <a
          href="https://workermill.com"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-300 transition-colors group"
        >
          {/* Layers icon */}
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
          Learn how WorkerMill builds software with AI workers
          <span className="group-hover:translate-x-0.5 transition-transform" aria-hidden="true">
            →
          </span>
        </a>
      </div>
    </section>
  );
}
