interface TechItem {
  emoji: string;
  name: string;
  subtitle: string;
}

const TECH_STACK: TechItem[] = [
  { emoji: "⚛️", name: "Next.js 16", subtitle: "App Router" },
  { emoji: "🔷", name: "Prisma 7", subtitle: "Type-safe ORM" },
  { emoji: "🐘", name: "PostgreSQL", subtitle: "Neon Serverless" },
  { emoji: "💨", name: "TailwindCSS v4", subtitle: "Utility-first CSS" },
];

interface TechStackProps {
  className?: string;
}

export function TechStack({ className }: TechStackProps) {
  return (
    <section
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16 border-t border-gray-800/50${className ? ` ${className}` : ""}`}
      aria-labelledby="stack-heading"
    >
      <div className="text-center mb-10">
        <h2 id="stack-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          Tech Stack
        </h2>
        <p className="text-gray-500">
          Production-grade Next.js dashboard — every technology chosen and implemented by AI workers
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl mx-auto">
        {TECH_STACK.map((tech) => (
          <div
            key={tech.name}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-center transition-all duration-200 hover:border-gray-700 hover:-translate-y-0.5"
          >
            <div className="text-3xl mb-3" aria-hidden="true">
              {tech.emoji}
            </div>
            <div className="font-semibold text-white text-sm">{tech.name}</div>
            <div className="text-xs text-gray-500 mt-1">{tech.subtitle}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
