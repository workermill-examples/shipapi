/**
 * Tests for GET /api/v1/showcase/stats
 *
 * Coverage
 * --------
 * - HTTP 200 with no auth header
 * - Response Content-Type is application/json
 * - Response body has exactly the expected integer fields
 * - All stat values are non-negative integers
 * - Endpoint is present in the OpenAPI spec under the "Showcase" tag
 *
 * These tests run against the live API endpoint (integration-level).
 * In CI the STATS_BASE_URL env var should point at the running server;
 * locally it defaults to http://localhost:8000.
 */

const BASE_URL = process.env.STATS_BASE_URL ?? "http://localhost:8000";
const STATS_ENDPOINT = `${BASE_URL}/api/v1/showcase/stats`;
const OPENAPI_ENDPOINT = `${BASE_URL}/openapi.json`;

/** Shape returned by GET /api/v1/showcase/stats */
interface ShowcaseStats {
  products: number;
  categories: number;
  warehouses: number;
  stock_alerts: number;
  stock_transfers: number;
  audit_log_entries: number;
}

const EXPECTED_KEYS: ReadonlyArray<keyof ShowcaseStats> = [
  "products",
  "categories",
  "warehouses",
  "stock_alerts",
  "stock_transfers",
  "audit_log_entries",
];

// ---------------------------------------------------------------------------
// HTTP response basics
// ---------------------------------------------------------------------------

describe("GET /api/v1/showcase/stats — HTTP basics", () => {
  it("returns HTTP 200", async () => {
    const res = await fetch(STATS_ENDPOINT);
    expect(res.status).toBe(200);
  });

  it("requires no authentication — responds 200 without an Authorization header", async () => {
    const res = await fetch(STATS_ENDPOINT);
    // Must not redirect to a login page or return 401/403
    expect(res.status).toBe(200);
  });

  it("returns Content-Type: application/json", async () => {
    const res = await fetch(STATS_ENDPOINT);
    expect(res.headers.get("content-type")).toMatch(/application\/json/);
  });
});

// ---------------------------------------------------------------------------
// JSON schema validation
// ---------------------------------------------------------------------------

describe("GET /api/v1/showcase/stats — JSON schema", () => {
  let body: ShowcaseStats;

  beforeAll(async () => {
    const res = await fetch(STATS_ENDPOINT);
    body = (await res.json()) as ShowcaseStats;
  });

  it("response body contains exactly the expected fields", () => {
    const keys = new Set(Object.keys(body));
    expect(keys).toEqual(new Set(EXPECTED_KEYS));
  });

  it.each(EXPECTED_KEYS)('field "%s" is an integer', (key) => {
    expect(Number.isInteger(body[key])).toBe(true);
  });

  it.each(EXPECTED_KEYS)('field "%s" is non-negative', (key) => {
    expect(body[key]).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// OpenAPI spec — endpoint registration and tagging
// ---------------------------------------------------------------------------

describe("GET /api/v1/showcase/stats — OpenAPI registration", () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let spec: Record<string, any>;

  beforeAll(async () => {
    const res = await fetch(OPENAPI_ENDPOINT);
    spec = (await res.json()) as Record<string, any>;
  });

  it("endpoint is present in the OpenAPI spec paths", () => {
    expect(spec.paths).toHaveProperty("/api/v1/showcase/stats");
  });

  it('endpoint GET operation is tagged "Showcase"', () => {
    const tags: string[] =
      (spec.paths["/api/v1/showcase/stats"]?.get?.tags as string[]) ?? [];
    expect(tags).toContain("Showcase");
  });
});
