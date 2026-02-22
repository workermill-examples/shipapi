/**
 * Landing page component render tests
 *
 * Coverage
 * --------
 * - Navbar: "TaskPulse" brand, "Built by WorkerMill" badge, nav links
 * - Hero: gradient title, WorkerMill attribution, "entirely by AI workers" copy,
 *         Try Demo and View Source CTAs, 5 epics / 36 stories feature text
 * - LiveStats: section heading, data source label, 6 stat card labels
 * - HowItWasBuilt: section heading, all 5 epic titles, 140 tests summary card,
 *                  WorkerMill attribution link
 * - DemoAccess: section heading, demo email, password, API key, "Open Dashboard" CTA
 * - Footer: brand attribution, Health / GitHub / WorkerMill footer links
 * - LandingPage (page.tsx): all major sections present in the assembled page
 *
 * Dependencies (provided by the surrounding Next.js / Jest setup):
 *   @testing-library/react, @testing-library/jest-dom, jest
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

// Component imports — adjust paths if the project moves to a different layout.
import { Navbar } from "../Navbar";
import { Hero } from "../Hero";
import { LiveStats } from "../LiveStats";
import { HowItWasBuilt } from "../HowItWasBuilt";
import { DemoAccess } from "../DemoAccess";
import { Footer } from "../Footer";
import LandingPage from "../../../app/page";

// ---------------------------------------------------------------------------
// Jest setup — suppress "fetch is not defined" noise from LiveStats useEffect
// ---------------------------------------------------------------------------

beforeEach(() => {
  // Provide a minimal fetch stub so LiveStats.useEffect does not throw.
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      products: 42,
      categories: 8,
      warehouses: 3,
      stock_alerts: 2,
      stock_transfers: 15,
      audit_log_entries: 300,
    }),
  } as Response);
});

afterEach(() => {
  jest.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Navbar
// ---------------------------------------------------------------------------

describe("Navbar", () => {
  it('renders the "TaskPulse" brand name', () => {
    render(<Navbar />);
    expect(screen.getByText("TaskPulse")).toBeInTheDocument();
  });

  it('renders the "Built by WorkerMill" badge', () => {
    render(<Navbar />);
    expect(screen.getByText(/Built by WorkerMill/i)).toBeInTheDocument();
  });

  it('links "Built by WorkerMill" to workermill.com', () => {
    render(<Navbar />);
    const link = screen.getByRole("link", { name: /Built by WorkerMill/i });
    expect(link).toHaveAttribute("href", "https://workermill.com");
  });

  it('renders "Try Demo" nav link', () => {
    render(<Navbar />);
    expect(screen.getByRole("link", { name: /Try Demo/i })).toBeInTheDocument();
  });

  it('renders "GitHub" nav link', () => {
    render(<Navbar />);
    expect(screen.getByRole("link", { name: /GitHub/i })).toBeInTheDocument();
  });

  it("GitHub nav link points to the taskpulse repository", () => {
    render(<Navbar />);
    const githubLink = screen.getByRole("link", { name: /GitHub/i });
    expect(githubLink).toHaveAttribute(
      "href",
      expect.stringContaining("github.com/workermill-examples/taskpulse")
    );
  });
});

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

describe("Hero", () => {
  it('renders the "TaskPulse" gradient title', () => {
    render(<Hero />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("TaskPulse");
  });

  it('renders "Live on Vercel · Deployed by AI Workers" badge', () => {
    render(<Hero />);
    expect(screen.getByText(/Live on Vercel · Deployed by AI Workers/i)).toBeInTheDocument();
  });

  it('subtitle mentions "entirely by AI workers"', () => {
    render(<Hero />);
    expect(screen.getByText(/entirely by AI workers/i)).toBeInTheDocument();
  });

  it("feature text mentions 5 epics and 36 stories", () => {
    render(<Hero />);
    expect(screen.getByText(/5 epics and 36 stories/i)).toBeInTheDocument();
  });

  it('renders "Try Demo" CTA link', () => {
    render(<Hero />);
    const links = screen.getAllByRole("link", { name: /Try Demo/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it('renders "View Source" CTA link pointing to GitHub', () => {
    render(<Hero />);
    const link = screen.getByRole("link", { name: /View Source/i });
    expect(link).toHaveAttribute(
      "href",
      expect.stringContaining("github.com/workermill-examples/taskpulse")
    );
  });

  it("WorkerMill link opens in a new tab with noopener", () => {
    render(<Hero />);
    const wm = screen.getByRole("link", { name: /WorkerMill/i });
    expect(wm).toHaveAttribute("target", "_blank");
    expect(wm).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});

// ---------------------------------------------------------------------------
// LiveStats
// ---------------------------------------------------------------------------

describe("LiveStats", () => {
  it('renders "Live Stats" section heading', () => {
    render(<LiveStats />);
    expect(screen.getByRole("heading", { name: /Live Stats/i })).toBeInTheDocument();
  });

  it("displays the stats API URL in the description label", () => {
    render(<LiveStats statsUrl="/api/v1/showcase/stats" />);
    expect(screen.getByText(/\/api\/v1\/showcase\/stats/)).toBeInTheDocument();
  });

  it("renders all 6 stat card labels", () => {
    render(<LiveStats />);
    const expectedLabels = [
      /Products/i,
      /Categories/i,
      /Warehouses/i,
      /Stock Alerts/i,
      /Transfers/i,
      /Audit Entries/i,
    ];
    for (const label of expectedLabels) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("section has accessible region label", () => {
    render(<LiveStats />);
    expect(screen.getByRole("region", { name: /Live statistics/i })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// HowItWasBuilt
// ---------------------------------------------------------------------------

describe("HowItWasBuilt", () => {
  it('renders "How It Was Built" section heading', () => {
    render(<HowItWasBuilt />);
    expect(screen.getByRole("heading", { name: /How It Was Built/i })).toBeInTheDocument();
  });

  it("displays the 5 epics · 36 stories · 140 tests summary line", () => {
    render(<HowItWasBuilt />);
    expect(screen.getByText(/5 epics · 36 stories · 140 tests/i)).toBeInTheDocument();
  });

  const EPIC_TITLES = [
    /Project Setup & Dev Environment/i,
    /Core API & Task Engine/i,
    /Dashboard UI/i,
    /Scheduling, API Keys & Polish/i,
    /Production Deploy & Validation/i,
  ];

  it.each(EPIC_TITLES)('renders epic card: %s', (title) => {
    render(<HowItWasBuilt />);
    expect(screen.getByText(title)).toBeInTheDocument();
  });

  it('renders the 140 tests-passing summary card', () => {
    render(<HowItWasBuilt />);
    // The large "140" number appears in the summary card
    expect(screen.getByText("140")).toBeInTheDocument();
    expect(screen.getByText(/Tests passing/i)).toBeInTheDocument();
  });

  it('renders WorkerMill "Learn how" attribution link', () => {
    render(<HowItWasBuilt />);
    const link = screen.getByRole("link", {
      name: /Learn how WorkerMill builds software with AI workers/i,
    });
    expect(link).toHaveAttribute("href", "https://workermill.com");
  });

  it('mentions "zero human-written lines of code"', () => {
    render(<HowItWasBuilt />);
    expect(screen.getByText(/zero human-written lines of code/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// DemoAccess
// ---------------------------------------------------------------------------

describe("DemoAccess", () => {
  it('renders "Demo Access" section heading', () => {
    render(<DemoAccess />);
    expect(screen.getByRole("heading", { name: /Demo Access/i })).toBeInTheDocument();
  });

  it("displays the demo email address", () => {
    render(<DemoAccess />);
    expect(screen.getByText("demo@workermill.com")).toBeInTheDocument();
  });

  it("displays the demo password", () => {
    render(<DemoAccess />);
    expect(screen.getByText("demo1234")).toBeInTheDocument();
  });

  it("displays the demo API key", () => {
    render(<DemoAccess />);
    expect(screen.getByLabelText(/Demo API key/i)).toHaveTextContent(
      "sk_demo_shipapi_2026_showcase_key"
    );
  });

  it('renders "Open Dashboard →" CTA link', () => {
    render(<DemoAccess />);
    const link = screen.getByRole("link", { name: /Open Dashboard/i });
    expect(link).toBeInTheDocument();
  });

  it("dashboard CTA opens in a new tab", () => {
    render(<DemoAccess />);
    const link = screen.getByRole("link", { name: /Open Dashboard/i });
    expect(link).toHaveAttribute("target", "_blank");
  });
});

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

describe("Footer", () => {
  it('renders "TaskPulse — built by WorkerMill AI workers" attribution', () => {
    render(<Footer />);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(/TaskPulse — built by/i);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(/WorkerMill/i);
    expect(screen.getByRole("contentinfo")).toHaveTextContent(/AI workers/i);
  });

  it('renders "Health" footer link to /api/v1/health', () => {
    render(<Footer />);
    const link = screen.getByRole("link", { name: /^Health$/i });
    expect(link).toHaveAttribute("href", "/api/v1/health");
  });

  it('renders "GitHub" footer link', () => {
    render(<Footer />);
    const links = screen.getAllByRole("link", { name: /^GitHub$/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links[0]).toHaveAttribute(
      "href",
      expect.stringContaining("github.com/workermill-examples/taskpulse")
    );
  });

  it('renders "WorkerMill" footer link to workermill.com', () => {
    render(<Footer />);
    const links = screen.getAllByRole("link", { name: /^WorkerMill$/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links[0]).toHaveAttribute("href", "https://workermill.com");
  });
});

// ---------------------------------------------------------------------------
// LandingPage (full page assembly)
// ---------------------------------------------------------------------------

describe("LandingPage (page.tsx)", () => {
  it("renders without crashing", () => {
    expect(() => render(<LandingPage />)).not.toThrow();
  });

  it("contains all required section headings", () => {
    render(<LandingPage />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("TaskPulse");
    expect(screen.getByRole("heading", { name: /Live Stats/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /How It Was Built/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Demo Access/i })).toBeInTheDocument();
  });

  it('has a visible navigation bar with "TaskPulse" brand', () => {
    render(<LandingPage />);
    expect(screen.getAllByText("TaskPulse").length).toBeGreaterThanOrEqual(1);
  });

  it("has a footer with WorkerMill attribution", () => {
    render(<LandingPage />);
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it("WorkerMill is mentioned multiple times (branding density check)", () => {
    const { container } = render(<LandingPage />);
    const html = container.innerHTML;
    const occurrences = (html.match(/WorkerMill/g) ?? []).length;
    // Nav badge + footer + HowItWasBuilt summary card + WorkerMill link in hero
    expect(occurrences).toBeGreaterThanOrEqual(4);
  });

  it('stats source label references "/api/v1/showcase/stats"', () => {
    render(<LandingPage />);
    expect(screen.getByText(/\/api\/v1\/showcase\/stats/)).toBeInTheDocument();
  });
});
