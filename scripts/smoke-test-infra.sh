#!/usr/bin/env bash
# smoke-test-infra.sh — Infrastructure smoke tests for ShipAPI
#
# Tests:
#   1. Health endpoint returns 200 with {status: ok, database: connected}
#   2. /docs (Swagger UI) loads with HTTP 200
#   3. /redoc (ReDoc) loads with HTTP 200
#   4. OpenAPI JSON contains all 7 expected tag groups
#   5. X-Request-Id header is present on every response
#   6. Rate limiting returns 429 on rapid requests (register endpoint: 5/min)
#   7. Error responses follow the standard {"error": {"code": "...", "message": "..."}} envelope
#
# Usage:
#   ./scripts/smoke-test-infra.sh [BASE_URL]
#
# Defaults to https://shipapi.workermill.com when BASE_URL is not supplied.
#
# Requirements: curl, jq

set -euo pipefail

BASE_URL="${1:-https://shipapi.workermill.com}"

# Trim trailing slash so every path below can start with /
BASE_URL="${BASE_URL%/}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS=0
FAIL=0
ERRORS=()

pass() {
    echo "  [PASS] $*"
    ((PASS++)) || true
}

fail() {
    echo "  [FAIL] $*"
    ERRORS+=("$*")
    ((FAIL++)) || true
}

section() {
    echo ""
    echo "==> $*"
}

# Run curl and capture the full response (headers + body) in a temp file.
# Usage: run_curl <temp_file> [extra curl args...] <url>
run_curl() {
    local outfile="$1"; shift
    curl --silent --show-error --dump-header - --max-time 15 "$@" >"$outfile" 2>&1
}

# Extract the HTTP status code from a dump-header response file.
http_status() {
    grep -m1 '^HTTP/' "$1" | awk '{print $2}'
}

# Extract a header value (case-insensitive) from a dump-header response file.
header_value() {
    local file="$1" header="$2"
    grep -i "^${header}:" "$file" | head -1 | sed 's/^[^:]*:[[:space:]]*//' | tr -d '\r'
}

# Extract the JSON body from a dump-header response file (everything after the blank line).
json_body() {
    awk 'found{print} /^\r?$/{found=1}' "$1"
}

# ---------------------------------------------------------------------------
# Temporary workspace
# ---------------------------------------------------------------------------

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------

section "1. Health endpoint — GET /api/v1/health"

HEALTH_OUT="$TMP/health.txt"
run_curl "$HEALTH_OUT" "${BASE_URL}/api/v1/health"

STATUS="$(http_status "$HEALTH_OUT")"
if [[ "$STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200, got $STATUS"
fi

BODY="$(json_body "$HEALTH_OUT")"

DB_STATUS="$(echo "$BODY" | jq -r '.database // empty' 2>/dev/null)"
APP_STATUS="$(echo "$BODY" | jq -r '.status // empty' 2>/dev/null)"

if [[ "$APP_STATUS" == "ok" ]]; then
    pass "Response field 'status' == 'ok'"
else
    fail "Expected status='ok', got '${APP_STATUS}'"
fi

if [[ "$DB_STATUS" == "connected" ]]; then
    pass "Response field 'database' == 'connected'"
else
    fail "Expected database='connected', got '${DB_STATUS}'"
fi

# X-Request-Id must be present (checked explicitly here and again in test 5)
REQ_ID="$(header_value "$HEALTH_OUT" "X-Request-Id")"
if [[ -n "$REQ_ID" ]]; then
    pass "X-Request-Id header present on health response: $REQ_ID"
else
    fail "X-Request-Id header missing on health response"
fi

# ---------------------------------------------------------------------------
# 2. Swagger UI — GET /docs
# ---------------------------------------------------------------------------

section "2. Swagger UI — GET /docs"

DOCS_OUT="$TMP/docs.txt"
run_curl "$DOCS_OUT" "${BASE_URL}/docs"

DOCS_STATUS="$(http_status "$DOCS_OUT")"
if [[ "$DOCS_STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200, got $DOCS_STATUS"
fi

DOCS_BODY="$(json_body "$DOCS_OUT")"
if echo "$DOCS_BODY" | grep -q "swagger" 2>/dev/null; then
    pass "Response body contains 'swagger' (Swagger UI marker)"
elif echo "$DOCS_BODY" | grep -qi "SwaggerUIBundle\|swagger-ui\|openapi" 2>/dev/null; then
    pass "Response body contains Swagger UI reference"
else
    fail "Response body does not appear to be Swagger UI HTML"
fi

# ---------------------------------------------------------------------------
# 3. ReDoc — GET /redoc
# ---------------------------------------------------------------------------

section "3. ReDoc — GET /redoc"

REDOC_OUT="$TMP/redoc.txt"
run_curl "$REDOC_OUT" "${BASE_URL}/redoc"

REDOC_STATUS="$(http_status "$REDOC_OUT")"
if [[ "$REDOC_STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200, got $REDOC_STATUS"
fi

REDOC_BODY="$(json_body "$REDOC_OUT")"
if echo "$REDOC_BODY" | grep -qi "redoc\|ReDoc" 2>/dev/null; then
    pass "Response body contains ReDoc reference"
else
    fail "Response body does not appear to be ReDoc HTML"
fi

# ---------------------------------------------------------------------------
# 4. OpenAPI JSON — all 7 tag groups present
# ---------------------------------------------------------------------------

section "4. OpenAPI JSON — GET /openapi.json"

OPENAPI_OUT="$TMP/openapi.txt"
run_curl "$OPENAPI_OUT" "${BASE_URL}/openapi.json"

OPENAPI_STATUS="$(http_status "$OPENAPI_OUT")"
if [[ "$OPENAPI_STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200, got $OPENAPI_STATUS"
fi

OPENAPI_BODY="$(json_body "$OPENAPI_OUT")"

EXPECTED_TAGS=("Health" "Auth" "Categories" "Products" "Warehouses" "Stock" "Audit")
for tag in "${EXPECTED_TAGS[@]}"; do
    if echo "$OPENAPI_BODY" | jq -e --arg t "$tag" '.tags[]? | select(.name == $t)' >/dev/null 2>&1; then
        pass "OpenAPI tag group present: $tag"
    else
        fail "OpenAPI tag group missing: $tag"
    fi
done

# ---------------------------------------------------------------------------
# 5. X-Request-Id header — present on all response types
# ---------------------------------------------------------------------------

section "5. X-Request-Id header on multiple endpoints"

for path in "/api/v1/health" "/docs" "/redoc" "/openapi.json"; do
    HDR_OUT="$TMP/hdr_$(echo "$path" | tr '/' '_').txt"
    run_curl "$HDR_OUT" "${BASE_URL}${path}"
    HDR_VAL="$(header_value "$HDR_OUT" "X-Request-Id")"
    if [[ -n "$HDR_VAL" ]]; then
        pass "X-Request-Id present on ${path}: $HDR_VAL"
    else
        fail "X-Request-Id missing on ${path}"
    fi
done

# Also verify it appears on a 404 (error path)
ERR_OUT="$TMP/hdr_404.txt"
run_curl "$ERR_OUT" "${BASE_URL}/api/v1/does-not-exist"
ERR_HDR="$(header_value "$ERR_OUT" "X-Request-Id")"
if [[ -n "$ERR_HDR" ]]; then
    pass "X-Request-Id present on 404 response: $ERR_HDR"
else
    fail "X-Request-Id missing on 404 response"
fi

# ---------------------------------------------------------------------------
# 6. Rate limiting — verify 429 after exceeding the register limit (5/min)
# ---------------------------------------------------------------------------

section "6. Rate limiting — POST /api/v1/auth/register (limit: 5/minute)"

echo "     Sending 6 rapid registration requests to trigger rate limit..."

RL_GOT_429=false
RL_OUT="$TMP/rl.txt"

for i in $(seq 1 6); do
    UNIQUE="smoke$(date +%s%N)${i}@example.com"
    run_curl "$RL_OUT" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${UNIQUE}\",\"name\":\"Smoke Test\",\"password\":\"SmokeTest123!\"}" \
        "${BASE_URL}/api/v1/auth/register"

    RL_STATUS="$(http_status "$RL_OUT")"
    if [[ "$RL_STATUS" == "429" ]]; then
        RL_GOT_429=true
        # Verify the 429 body follows the error envelope
        RL_BODY="$(json_body "$RL_OUT")"
        RL_CODE="$(echo "$RL_BODY" | jq -r '.error.code // empty' 2>/dev/null)"
        RL_MSG="$(echo "$RL_BODY" | jq -r '.error.message // empty' 2>/dev/null)"
        if [[ -n "$RL_CODE" && -n "$RL_MSG" ]]; then
            pass "429 body follows error envelope: code=$RL_CODE"
        else
            fail "429 body does not follow error envelope: $(echo "$RL_BODY" | head -c 200)"
        fi
        break
    fi
done

if $RL_GOT_429; then
    pass "Rate limit enforced — received 429 after rapid requests"
else
    fail "Rate limit not triggered — never received 429 after 6 requests"
fi

# ---------------------------------------------------------------------------
# 7. Error response format — standard {"error": {"code": "...", "message": "..."}}
# ---------------------------------------------------------------------------

section "7. Error response format"

# 7a. 404 — unknown route
NOT_FOUND_OUT="$TMP/err_404.txt"
run_curl "$NOT_FOUND_OUT" "${BASE_URL}/api/v1/does-not-exist"

NF_STATUS="$(http_status "$NOT_FOUND_OUT")"
NF_BODY="$(json_body "$NOT_FOUND_OUT")"
NF_CODE="$(echo "$NF_BODY" | jq -r '.error.code // empty' 2>/dev/null)"
NF_MSG="$(echo "$NF_BODY" | jq -r '.error.message // empty' 2>/dev/null)"

if [[ "$NF_STATUS" == "404" ]]; then
    pass "404 response has correct HTTP status"
else
    fail "Expected 404, got $NF_STATUS"
fi

if [[ -n "$NF_CODE" && -n "$NF_MSG" ]]; then
    pass "404 response follows error envelope: code=$NF_CODE"
else
    fail "404 response missing error envelope — body: $(echo "$NF_BODY" | head -c 200)"
fi

# 7b. 401 — protected endpoint without credentials
UNAUTH_OUT="$TMP/err_401.txt"
run_curl "$UNAUTH_OUT" "${BASE_URL}/api/v1/auth/me"

UA_STATUS="$(http_status "$UNAUTH_OUT")"
UA_BODY="$(json_body "$UNAUTH_OUT")"
UA_CODE="$(echo "$UA_BODY" | jq -r '.error.code // empty' 2>/dev/null)"
UA_MSG="$(echo "$UA_BODY" | jq -r '.error.message // empty' 2>/dev/null)"

if [[ "$UA_STATUS" == "401" ]]; then
    pass "401 response has correct HTTP status"
else
    fail "Expected 401, got $UA_STATUS"
fi

if [[ -n "$UA_CODE" && -n "$UA_MSG" ]]; then
    pass "401 response follows error envelope: code=$UA_CODE"
else
    fail "401 response missing error envelope — body: $(echo "$UA_BODY" | head -c 200)"
fi

# 7c. 422 — validation error (bad login payload)
VAL_OUT="$TMP/err_422.txt"
run_curl "$VAL_OUT" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"not-an-email"}' \
    "${BASE_URL}/api/v1/auth/login"

VAL_STATUS="$(http_status "$VAL_OUT")"
VAL_BODY="$(json_body "$VAL_OUT")"
VAL_CODE="$(echo "$VAL_BODY" | jq -r '.error.code // empty' 2>/dev/null)"
VAL_MSG="$(echo "$VAL_BODY" | jq -r '.error.message // empty' 2>/dev/null)"

if [[ "$VAL_STATUS" == "422" ]]; then
    pass "422 response has correct HTTP status"
else
    fail "Expected 422, got $VAL_STATUS"
fi

if [[ -n "$VAL_CODE" && -n "$VAL_MSG" ]]; then
    pass "422 response follows error envelope: code=$VAL_CODE"
else
    fail "422 response missing error envelope — body: $(echo "$VAL_BODY" | head -c 200)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "========================================"
echo "  Smoke test results: $PASS passed, $FAIL failed"
echo "========================================"

if [[ ${#ERRORS[@]} -gt 0 ]]; then
    echo ""
    echo "Failures:"
    for err in "${ERRORS[@]}"; do
        echo "  - $err"
    done
    echo ""
    exit 1
fi

echo ""
echo "All infrastructure smoke tests passed."
exit 0
