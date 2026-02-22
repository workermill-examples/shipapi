import { CodeQuality } from "../components/showcase/CodeQuality";
import { DashboardPreview } from "../components/showcase/DashboardPreview";
import { DemoAccess } from "../components/showcase/DemoAccess";
import { Footer } from "../components/showcase/Footer";
import { Hero } from "../components/showcase/Hero";
import { HowItWasBuilt } from "../components/showcase/HowItWasBuilt";
import { LiveStats } from "../components/showcase/LiveStats";
import { Navbar } from "../components/showcase/Navbar";
import { TechStack } from "../components/showcase/TechStack";

const GITHUB_URL = "https://github.com/workermill-examples/taskpulse";
const DASHBOARD_URL = "https://taskpulse.workermill.com";

export default function LandingPage() {
  return (
    <div className="bg-gray-950 text-gray-100 min-h-screen antialiased">
      <Navbar demoUrl="#demo" githubUrl={GITHUB_URL} />
      <main>
        <Hero demoUrl="#demo" githubUrl={GITHUB_URL} />
        <LiveStats statsUrl="/api/v1/showcase/stats" />
        <TechStack />
        <DashboardPreview explorerUrl="#explorer-preview" docsUrl="/docs" />
        <HowItWasBuilt />
        <CodeQuality githubUrl={GITHUB_URL} />
        <DemoAccess dashboardUrl={DASHBOARD_URL} githubUrl={GITHUB_URL} />
      </main>
      <Footer githubUrl={GITHUB_URL} />
    </div>
  );
}
