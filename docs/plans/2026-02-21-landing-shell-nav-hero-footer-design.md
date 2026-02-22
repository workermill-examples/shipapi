# Landing Shell — Nav, Hero, Footer Design

**Date:** 2026-02-21
**Story:** TP-6/1 — Landing Shell — Nav, Hero, Footer
**Scope:** `src/components/showcase/Navbar.tsx`, `Hero.tsx`, `Footer.tsx`

---

## Context

The ShipAPI project's existing `src/templates/landing.html` (624 lines) serves as the design reference. This document describes three React TypeScript components that replicate the Nav, Hero, and Footer sections of that design with TaskPulse branding.

### Design Language (from `landing.html`)
- **Background**: `bg-gray-950` (#030712)
- **Text**: `text-gray-100`
- **Borders**: `border-gray-800/50`
- **Gradient text**: `linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #34d399 100%)`
- **Logo gradient**: `from-blue-500 to-purple-600`
- **Typography**: Inter font, JetBrains Mono for code

---

## Component Designs

### 1. Navbar

**Structure:**
- Sticky, `backdrop-blur-md`, `bg-gray-950/90`
- Left: Logo pill (gradient "T" letter) + "TaskPulse" text + WorkerMill badge
- Right: Nav links + GitHub CTA button

**Props:**
```tsx
interface NavbarProps {
  githubUrl?: string;
  demoUrl?: string;
}
```

**Key elements:**
- Logo: `w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600`, letter "T"
- WorkerMill badge: layers icon SVG + "Built by WorkerMill" text, links to `https://workermill.com`
- Nav links: "Try Demo" → `#demo`, "GitHub" → GitHub button (styled)
- All links have hover transitions, keyboard accessible

---

### 2. Hero

**Structure:**
- Full-width centered section, `max-w-7xl mx-auto`, `pt-20 pb-16`
- Pill badge → Gradient title → Subtitle → Feature list → CTA buttons

**Props:**
```tsx
interface HeroProps {
  demoUrl?: string;
  githubUrl?: string;
}
```

**Key elements:**
- Live badge: animated green dot + "Live on Vercel · Deployed by AI Workers"
- Title: `text-5xl sm:text-7xl font-extrabold` with `gradient-text` class
- Subtitle: "A real-time background task monitoring dashboard — written, tested, and deployed entirely by AI workers."
- Feature highlights: "Task registry · Cron scheduling · Real-time traces · Log streaming · API key management · Global search · Keyboard shortcuts — all built by WorkerMill AI agents across 5 epics and 36 stories."
- CTAs: Primary blue ("Try Demo") + secondary gray ("View Source")

---

### 3. Footer

**Structure:**
- `border-t border-gray-800/50`, responsive flex row/column
- Left: Small logo + attribution text
- Right: Footer nav links

**Props:** None (static content)

**Key elements:**
- Logo: `w-7 h-7` version of the gradient pill
- Attribution: "TaskPulse — built by WorkerMill AI workers"
- Links: Health (`/api/v1/health`), GitHub, WorkerMill

---

## Implementation Decisions

**DEC-001**: Using inline Tailwind classes (not a separate CSS file) — consistent with the existing landing.html pattern.

**DEC-002**: Components are self-contained with no external dependencies beyond React and Tailwind — allows usage in any React/Next.js project.

**DEC-003**: Using `cn()` utility pattern with a simple fallback if `clsx`/`cn` isn't available — components stay portable.

**DEC-004**: SVG icons are inlined (not from a library) — matches the landing.html approach and avoids external icon dependencies.

---

## File Structure

```
src/
  components/
    showcase/
      Navbar.tsx    # Sticky navigation bar
      Hero.tsx      # Hero section with badge, title, CTAs
      Footer.tsx    # Site footer with attribution
```
