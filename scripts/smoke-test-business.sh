#!/usr/bin/env bash
# smoke-test-business.sh — Business logic smoke tests for ShipAPI
#
# Tests:
#   1. Setup: login as demo admin to obtain JWT for subsequent tests
#   2. Product search: GET /products?search=monitor returns relevant results
#   3. Product search with filters: category_id + min_price + sort_by=price works
#   4. Stock transfer setup: set known stock levels for transfer testing
#   5. Stock transfer: execute transfer, verify source decremented + destination incremented
#   6. Insufficient stock: transfer exceeding available stock returns 400 INSUFFICIENT_STOCK
#   7. Stock alerts: GET /stock/alerts returns low-stock items with deficit field
#   8. Audit log: admin access returns entries; action and resource_type filters work
#
# Usage:
#   ./scripts/smoke-test-business.sh [BASE_URL]
#
# Defaults to https://shipapi.workermill.com when BASE_URL is not supplied.
#
# Requirements: curl, jq

set -euo pipefail

BASE_URL="${1:-https://shipapi.workermill.com}"

# Trim trailing slash so every path below can start with /
BASE_URL="${BASE_URL%/}"

# ---------------------------------------------------------------------------
# Helpers (same pattern as smoke-test-infra.sh)
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
# 1. Setup — Login as demo admin
# ---------------------------------------------------------------------------

section "1. Setup — POST /api/v1/auth/login (demo admin)"

DEMO_LOGIN_OUT="$TMP/demo_login.txt"
run_curl "$DEMO_LOGIN_OUT" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"email":"demo@workermill.com","password":"demo1234"}' \
    "${BASE_URL}/api/v1/auth/login"

DEMO_LOGIN_STATUS="$(http_status "$DEMO_LOGIN_OUT")"
DEMO_LOGIN_BODY="$(json_body "$DEMO_LOGIN_OUT")"
ADMIN_TOKEN="$(echo "$DEMO_LOGIN_BODY" | jq -r '.access_token // empty' 2>/dev/null)"

if [[ "$DEMO_LOGIN_STATUS" == "200" ]]; then
    pass "Demo admin login returns HTTP 200"
else
    fail "Expected HTTP 200 for demo login, got $DEMO_LOGIN_STATUS"
fi

if [[ -n "$ADMIN_TOKEN" ]]; then
    pass "Demo admin login returns access_token"
else
    fail "Demo admin login missing access_token — subsequent auth-protected tests will fail"
fi

# ---------------------------------------------------------------------------
# 2. Product search — GET /api/v1/products?search=monitor
# ---------------------------------------------------------------------------

section "2. Product keyword search — GET /api/v1/products?search=monitor"

SEARCH_OUT="$TMP/search_monitor.txt"
run_curl "$SEARCH_OUT" "${BASE_URL}/api/v1/products?search=monitor"

SEARCH_STATUS="$(http_status "$SEARCH_OUT")"
if [[ "$SEARCH_STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200, got $SEARCH_STATUS"
fi

SEARCH_BODY="$(json_body "$SEARCH_OUT")"
SEARCH_TOTAL="$(echo "$SEARCH_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
SEARCH_PAGE="$(echo "$SEARCH_BODY" | jq -r '.pagination.page // empty' 2>/dev/null)"
SEARCH_PER_PAGE="$(echo "$SEARCH_BODY" | jq -r '.pagination.per_page // empty' 2>/dev/null)"
SEARCH_COUNT="$(echo "$SEARCH_BODY" | jq -r '.data | length' 2>/dev/null)"

if [[ -n "$SEARCH_TOTAL" && "$SEARCH_TOTAL" != "0" ]]; then
    pass "Search for 'monitor' returned $SEARCH_TOTAL result(s)"
else
    fail "Expected at least one result for search='monitor', got total='${SEARCH_TOTAL}'"
fi

if [[ -n "$SEARCH_COUNT" && "$SEARCH_COUNT" -gt "0" ]]; then
    pass "Search response data array has $SEARCH_COUNT item(s) on current page"
else
    fail "Expected non-empty data array for search='monitor'"
fi

# Verify at least one result is relevant — name or description contains "monitor"
MONITOR_MATCH="$(echo "$SEARCH_BODY" | jq -r \
    '[.data[] | select(
        ((.name // "") | ascii_downcase | contains("monitor")) or
        ((.description // "") | ascii_downcase | contains("monitor"))
    )] | length' 2>/dev/null)"
if [[ -n "$MONITOR_MATCH" && "$MONITOR_MATCH" -gt "0" ]]; then
    pass "At least $MONITOR_MATCH result(s) contain 'monitor' in name or description"
else
    fail "No results contain 'monitor' in name or description — full-text search may not be working"
fi

# Verify pagination envelope shape
if [[ -n "$SEARCH_PAGE" && -n "$SEARCH_PER_PAGE" ]]; then
    pass "Pagination envelope present: page=$SEARCH_PAGE, per_page=$SEARCH_PER_PAGE, total=$SEARCH_TOTAL"
else
    fail "Pagination envelope missing page or per_page fields"
fi

# ---------------------------------------------------------------------------
# 3. Product search with filters — category_id + min_price + sort_by=price
# ---------------------------------------------------------------------------

section "3. Product search with filters — category_id + min_price + sort_by=price"

# Fetch the product list (public endpoint) to extract a real category_id for filtering
PROD_LIST_OUT="$TMP/prod_list.txt"
run_curl "$PROD_LIST_OUT" "${BASE_URL}/api/v1/products"

PROD_LIST_BODY="$(json_body "$PROD_LIST_OUT")"
FILTER_CATEGORY_ID="$(echo "$PROD_LIST_BODY" | jq -r '.data[0].category.id // empty' 2>/dev/null)"
FILTER_CATEGORY_NAME="$(echo "$PROD_LIST_BODY" | jq -r '.data[0].category.name // empty' 2>/dev/null)"

if [[ -n "$FILTER_CATEGORY_ID" ]]; then
    pass "Extracted category_id for filter test: $FILTER_CATEGORY_NAME ($FILTER_CATEGORY_ID)"
else
    fail "Could not extract category_id from product list — skipping filter sub-checks"
fi

if [[ -n "$FILTER_CATEGORY_ID" ]]; then
    FILTER_OUT="$TMP/filter_search.txt"
    run_curl "$FILTER_OUT" \
        "${BASE_URL}/api/v1/products?category_id=${FILTER_CATEGORY_ID}&min_price=10&sort_by=price&sort_order=asc"

    FILTER_STATUS="$(http_status "$FILTER_OUT")"
    if [[ "$FILTER_STATUS" == "200" ]]; then
        pass "Filtered search (category_id + min_price + sort_by=price) returns HTTP 200"
    else
        fail "Expected HTTP 200 for filtered search, got $FILTER_STATUS"
    fi

    FILTER_BODY="$(json_body "$FILTER_OUT")"
    FILTER_TOTAL="$(echo "$FILTER_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
    FILTER_COUNT="$(echo "$FILTER_BODY" | jq -r '.data | length' 2>/dev/null)"

    if [[ -n "$FILTER_TOTAL" && "$FILTER_TOTAL" -gt "0" ]]; then
        pass "Filtered search returned $FILTER_TOTAL result(s) for category '$FILTER_CATEGORY_NAME'"
    else
        fail "Expected results for category_id+min_price+sort_by filter, got total='${FILTER_TOTAL}'"
    fi

    # Verify min_price filter: no result has price < 10
    BELOW_MIN="$(echo "$FILTER_BODY" | \
        jq -r '[.data[] | select((.price // "0") | tonumber < 10)] | length' 2>/dev/null)"
    if [[ "$BELOW_MIN" == "0" ]]; then
        pass "All results have price >= 10 (min_price filter applied correctly)"
    else
        fail "$BELOW_MIN result(s) have price < 10 — min_price filter not applied"
    fi

    # Verify sort_by=price ascending: first item price <= second item price
    if [[ -n "$FILTER_COUNT" && "$FILTER_COUNT" -ge "2" ]]; then
        FIRST_PRICE="$(echo "$FILTER_BODY" | jq -r '.data[0].price // "0"' 2>/dev/null)"
        SECOND_PRICE="$(echo "$FILTER_BODY" | jq -r '.data[1].price // "0"' 2>/dev/null)"
        SORTED_ASC="$(echo "$FILTER_BODY" | \
            jq -r 'if ((.data[0].price // "0") | tonumber) <= ((.data[1].price // "0") | tonumber)
                   then "yes" else "no" end' 2>/dev/null)"
        if [[ "$SORTED_ASC" == "yes" ]]; then
            pass "Results sorted ascending by price: $FIRST_PRICE <= $SECOND_PRICE"
        else
            fail "Results not sorted ascending — first=$FIRST_PRICE, second=$SECOND_PRICE"
        fi
    else
        echo "  [INFO] Only 1 result in category — sort order check requires at least 2"
        pass "Sort order check skipped (single result)"
    fi
fi

# ---------------------------------------------------------------------------
# 4. Stock transfer setup — set known stock levels
# ---------------------------------------------------------------------------

section "4. Stock transfer setup — PUT /api/v1/stock/{product_id}/{warehouse_id}"

# Find the ProSound Wireless Earbuds (ELEC-ACC-001) via keyword search
EARBUDS_OUT="$TMP/earbuds_search.txt"
run_curl "$EARBUDS_OUT" "${BASE_URL}/api/v1/products?search=earbuds"

EARBUDS_BODY="$(json_body "$EARBUDS_OUT")"
EARBUDS_ID="$(echo "$EARBUDS_BODY" | jq -r '.data[0].id // empty' 2>/dev/null)"
EARBUDS_NAME="$(echo "$EARBUDS_BODY" | jq -r '.data[0].name // empty' 2>/dev/null)"

if [[ -n "$EARBUDS_ID" ]]; then
    pass "Found product for transfer test: $EARBUDS_NAME ($EARBUDS_ID)"
else
    fail "Could not find earbuds product via search — stock transfer tests will be skipped"
fi

# Find East Coast Hub and West Coast Hub warehouse IDs
WH_LIST_OUT="$TMP/warehouse_list.txt"
run_curl "$WH_LIST_OUT" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/api/v1/warehouses"

WH_LIST_STATUS="$(http_status "$WH_LIST_OUT")"
WH_LIST_BODY="$(json_body "$WH_LIST_OUT")"

if [[ "$WH_LIST_STATUS" == "200" ]]; then
    pass "Warehouse list returned HTTP 200"
else
    fail "Expected HTTP 200 for warehouse list, got $WH_LIST_STATUS"
fi

EAST_WH_ID="$(echo "$WH_LIST_BODY" | \
    jq -r '.data[] | select(.name == "East Coast Hub") | .id' 2>/dev/null | head -1)"
WEST_WH_ID="$(echo "$WH_LIST_BODY" | \
    jq -r '.data[] | select(.name == "West Coast Hub") | .id' 2>/dev/null | head -1)"

if [[ -n "$EAST_WH_ID" ]]; then
    pass "Found East Coast Hub warehouse: $EAST_WH_ID"
else
    fail "Could not find East Coast Hub warehouse in list"
fi

if [[ -n "$WEST_WH_ID" ]]; then
    pass "Found West Coast Hub warehouse: $WEST_WH_ID"
else
    fail "Could not find West Coast Hub warehouse in list"
fi

# Set East Coast Hub stock to 100 units (source for transfer test)
if [[ -n "$EARBUDS_ID" && -n "$EAST_WH_ID" ]]; then
    STOCK_EAST_OUT="$TMP/stock_east_set.txt"
    run_curl "$STOCK_EAST_OUT" \
        -X PUT \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"quantity":100,"min_threshold":20}' \
        "${BASE_URL}/api/v1/stock/${EARBUDS_ID}/${EAST_WH_ID}"

    STOCK_EAST_STATUS="$(http_status "$STOCK_EAST_OUT")"
    STOCK_EAST_BODY="$(json_body "$STOCK_EAST_OUT")"
    STOCK_EAST_QTY="$(echo "$STOCK_EAST_BODY" | jq -r '.quantity // empty' 2>/dev/null)"

    if [[ "$STOCK_EAST_STATUS" == "200" && "$STOCK_EAST_QTY" == "100" ]]; then
        pass "East Coast Hub stock set to quantity=$STOCK_EAST_QTY"
    else
        fail "Expected HTTP 200 with quantity=100, got status=$STOCK_EAST_STATUS qty='${STOCK_EAST_QTY}'"
    fi
fi

# Set West Coast Hub stock to 50 units (destination for transfer test)
if [[ -n "$EARBUDS_ID" && -n "$WEST_WH_ID" ]]; then
    STOCK_WEST_OUT="$TMP/stock_west_set.txt"
    run_curl "$STOCK_WEST_OUT" \
        -X PUT \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d '{"quantity":50,"min_threshold":10}' \
        "${BASE_URL}/api/v1/stock/${EARBUDS_ID}/${WEST_WH_ID}"

    STOCK_WEST_STATUS="$(http_status "$STOCK_WEST_OUT")"
    STOCK_WEST_BODY="$(json_body "$STOCK_WEST_OUT")"
    STOCK_WEST_QTY="$(echo "$STOCK_WEST_BODY" | jq -r '.quantity // empty' 2>/dev/null)"

    if [[ "$STOCK_WEST_STATUS" == "200" && "$STOCK_WEST_QTY" == "50" ]]; then
        pass "West Coast Hub stock set to quantity=$STOCK_WEST_QTY"
    else
        fail "Expected HTTP 200 with quantity=50, got status=$STOCK_WEST_STATUS qty='${STOCK_WEST_QTY}'"
    fi
fi

# ---------------------------------------------------------------------------
# 5. Stock transfer — execute and verify source/destination balance change
# ---------------------------------------------------------------------------

section "5. Stock transfer — POST /api/v1/stock/transfer"

TRANSFER_QTY=10

if [[ -n "$EARBUDS_ID" && -n "$EAST_WH_ID" && -n "$WEST_WH_ID" ]]; then
    TRANSFER_OUT="$TMP/transfer.txt"
    run_curl "$TRANSFER_OUT" \
        -X POST \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"product_id\":\"${EARBUDS_ID}\",\"from_warehouse_id\":\"${EAST_WH_ID}\",\"to_warehouse_id\":\"${WEST_WH_ID}\",\"quantity\":${TRANSFER_QTY},\"notes\":\"Business smoke test transfer\"}" \
        "${BASE_URL}/api/v1/stock/transfer"

    TRANSFER_STATUS="$(http_status "$TRANSFER_OUT")"
    if [[ "$TRANSFER_STATUS" == "201" ]]; then
        pass "Stock transfer returns HTTP 201 Created"
    else
        fail "Expected HTTP 201 for stock transfer, got $TRANSFER_STATUS"
    fi

    TRANSFER_BODY="$(json_body "$TRANSFER_OUT")"
    TRANSFER_ID="$(echo "$TRANSFER_BODY" | jq -r '.id // empty' 2>/dev/null)"
    TRANSFER_PROD_ID="$(echo "$TRANSFER_BODY" | jq -r '.product_id // empty' 2>/dev/null)"
    TRANSFER_FROM_WH="$(echo "$TRANSFER_BODY" | jq -r '.from_warehouse_id // empty' 2>/dev/null)"
    TRANSFER_TO_WH="$(echo "$TRANSFER_BODY" | jq -r '.to_warehouse_id // empty' 2>/dev/null)"
    TRANSFER_QTY_RESP="$(echo "$TRANSFER_BODY" | jq -r '.quantity // empty' 2>/dev/null)"
    TRANSFER_INITIATED="$(echo "$TRANSFER_BODY" | jq -r '.initiated_by // empty' 2>/dev/null)"
    TRANSFER_CREATED="$(echo "$TRANSFER_BODY" | jq -r '.created_at // empty' 2>/dev/null)"

    if [[ -n "$TRANSFER_ID" ]]; then
        pass "Transfer record has id: $TRANSFER_ID"
    else
        fail "Transfer response missing id field"
    fi

    if [[ "$TRANSFER_PROD_ID" == "$EARBUDS_ID" ]]; then
        pass "Transfer record has correct product_id"
    else
        fail "Transfer product_id mismatch: expected $EARBUDS_ID, got '${TRANSFER_PROD_ID}'"
    fi

    if [[ "$TRANSFER_FROM_WH" == "$EAST_WH_ID" ]]; then
        pass "Transfer record has correct from_warehouse_id (East Coast Hub)"
    else
        fail "Transfer from_warehouse_id mismatch: expected $EAST_WH_ID, got '${TRANSFER_FROM_WH}'"
    fi

    if [[ "$TRANSFER_TO_WH" == "$WEST_WH_ID" ]]; then
        pass "Transfer record has correct to_warehouse_id (West Coast Hub)"
    else
        fail "Transfer to_warehouse_id mismatch: expected $WEST_WH_ID, got '${TRANSFER_TO_WH}'"
    fi

    if [[ "$TRANSFER_QTY_RESP" == "$TRANSFER_QTY" ]]; then
        pass "Transfer record has correct quantity: $TRANSFER_QTY_RESP"
    else
        fail "Transfer quantity mismatch: expected $TRANSFER_QTY, got '${TRANSFER_QTY_RESP}'"
    fi

    if [[ -n "$TRANSFER_INITIATED" ]]; then
        pass "Transfer record has initiated_by: $TRANSFER_INITIATED"
    else
        fail "Transfer response missing initiated_by field"
    fi

    if [[ -n "$TRANSFER_CREATED" ]]; then
        pass "Transfer record has created_at timestamp"
    else
        fail "Transfer response missing created_at field"
    fi

    # Verify stock balance change via product detail endpoint (includes stock_levels)
    PROD_DETAIL_OUT="$TMP/prod_detail_post_transfer.txt"
    run_curl "$PROD_DETAIL_OUT" "${BASE_URL}/api/v1/products/${EARBUDS_ID}"

    PROD_DETAIL_BODY="$(json_body "$PROD_DETAIL_OUT")"
    EAST_QTY_AFTER="$(echo "$PROD_DETAIL_BODY" | \
        jq -r --arg wh_id "$EAST_WH_ID" \
        '.stock_levels[] | select(.warehouse_id == $wh_id) | .quantity // empty' 2>/dev/null)"
    WEST_QTY_AFTER="$(echo "$PROD_DETAIL_BODY" | \
        jq -r --arg wh_id "$WEST_WH_ID" \
        '.stock_levels[] | select(.warehouse_id == $wh_id) | .quantity // empty' 2>/dev/null)"

    EXPECTED_EAST=90   # 100 - 10
    EXPECTED_WEST=60   # 50 + 10

    if [[ "$EAST_QTY_AFTER" == "$EXPECTED_EAST" ]]; then
        pass "Source (East Coast Hub) decremented: $EAST_QTY_AFTER (was 100, transferred $TRANSFER_QTY)"
    else
        fail "Source quantity mismatch: expected $EXPECTED_EAST, got '${EAST_QTY_AFTER}'"
    fi

    if [[ "$WEST_QTY_AFTER" == "$EXPECTED_WEST" ]]; then
        pass "Destination (West Coast Hub) incremented: $WEST_QTY_AFTER (was 50, received $TRANSFER_QTY)"
    else
        fail "Destination quantity mismatch: expected $EXPECTED_WEST, got '${WEST_QTY_AFTER}'"
    fi
else
    echo "  [INFO] Skipping transfer execution — missing product or warehouse IDs from setup"
    pass "Transfer execution skipped (setup failed to resolve IDs)"
fi

# ---------------------------------------------------------------------------
# 6. Insufficient stock — quantity exceeds available stock
# ---------------------------------------------------------------------------

section "6. Insufficient stock — POST /api/v1/stock/transfer (quantity > available)"

if [[ -n "$EARBUDS_ID" && -n "$EAST_WH_ID" && -n "$WEST_WH_ID" ]]; then
    INSUFF_OUT="$TMP/transfer_insuff.txt"
    run_curl "$INSUFF_OUT" \
        -X POST \
        -H "Authorization: Bearer ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"product_id\":\"${EARBUDS_ID}\",\"from_warehouse_id\":\"${EAST_WH_ID}\",\"to_warehouse_id\":\"${WEST_WH_ID}\",\"quantity\":5000}" \
        "${BASE_URL}/api/v1/stock/transfer"

    INSUFF_STATUS="$(http_status "$INSUFF_OUT")"
    if [[ "$INSUFF_STATUS" == "400" ]]; then
        pass "Transfer with quantity > stock returns HTTP 400"
    else
        fail "Expected HTTP 400 for insufficient stock transfer, got $INSUFF_STATUS"
    fi

    INSUFF_BODY="$(json_body "$INSUFF_OUT")"
    INSUFF_MSG="$(echo "$INSUFF_BODY" | jq -r '.error.message // empty' 2>/dev/null)"
    INSUFF_CODE="$(echo "$INSUFF_BODY" | jq -r '.error.code // empty' 2>/dev/null)"

    if [[ "$INSUFF_MSG" == *"INSUFFICIENT_STOCK"* ]]; then
        pass "400 error message contains INSUFFICIENT_STOCK"
    elif [[ -n "$INSUFF_CODE" || -n "$INSUFF_MSG" ]]; then
        fail "Expected INSUFFICIENT_STOCK in error.message, got code='${INSUFF_CODE}' message='${INSUFF_MSG}'"
    else
        fail "400 response missing error envelope — body: $(echo "$INSUFF_BODY" | head -c 200)"
    fi

    # Verify atomicity: source stock level was NOT changed by the failed transfer
    ATOMIC_OUT="$TMP/prod_detail_atomic.txt"
    run_curl "$ATOMIC_OUT" "${BASE_URL}/api/v1/products/${EARBUDS_ID}"

    ATOMIC_BODY="$(json_body "$ATOMIC_OUT")"
    EAST_QTY_ATOMIC="$(echo "$ATOMIC_BODY" | \
        jq -r --arg wh_id "$EAST_WH_ID" \
        '.stock_levels[] | select(.warehouse_id == $wh_id) | .quantity // empty' 2>/dev/null)"

    if [[ "$EAST_QTY_ATOMIC" == "90" ]]; then
        pass "Insufficient stock transfer is atomic — source quantity unchanged at 90"
    else
        fail "Atomicity check failed: expected source=90 (unchanged), got '${EAST_QTY_ATOMIC}'"
    fi
else
    echo "  [INFO] Skipping insufficient-stock test — missing product or warehouse IDs from setup"
    pass "Insufficient stock test skipped (setup failed to resolve IDs)"
fi

# ---------------------------------------------------------------------------
# 7. Stock alerts — GET /api/v1/stock/alerts
# ---------------------------------------------------------------------------

section "7. Stock alerts — GET /api/v1/stock/alerts"

ALERTS_OUT="$TMP/stock_alerts.txt"
run_curl "$ALERTS_OUT" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/api/v1/stock/alerts"

ALERTS_STATUS="$(http_status "$ALERTS_OUT")"
if [[ "$ALERTS_STATUS" == "200" ]]; then
    pass "HTTP status is 200"
else
    fail "Expected HTTP 200 for stock alerts, got $ALERTS_STATUS"
fi

ALERTS_BODY="$(json_body "$ALERTS_OUT")"
ALERTS_TOTAL="$(echo "$ALERTS_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
ALERTS_COUNT="$(echo "$ALERTS_BODY" | jq -r '.data | length' 2>/dev/null)"

if [[ -n "$ALERTS_TOTAL" && "$ALERTS_TOTAL" -ge "10" ]]; then
    pass "Stock alerts total is $ALERTS_TOTAL (>= 10 low-stock products seeded)"
else
    fail "Expected at least 10 stock alerts (seeded data), got total='${ALERTS_TOTAL}'"
fi

if [[ -n "$ALERTS_COUNT" && "$ALERTS_COUNT" -gt "0" ]]; then
    pass "Stock alerts data array has $ALERTS_COUNT item(s) on current page"
else
    fail "Expected non-empty data array in stock alerts response"
fi

# Verify alert item schema
ALERT_PRODUCT_ID="$(echo "$ALERTS_BODY" | jq -r '.data[0].product.id // empty' 2>/dev/null)"
ALERT_PRODUCT_NAME="$(echo "$ALERTS_BODY" | jq -r '.data[0].product.name // empty' 2>/dev/null)"
ALERT_WAREHOUSE_ID="$(echo "$ALERTS_BODY" | jq -r '.data[0].warehouse.id // empty' 2>/dev/null)"
ALERT_QTY="$(echo "$ALERTS_BODY" | jq -r '.data[0].quantity // empty' 2>/dev/null)"
ALERT_THRESHOLD="$(echo "$ALERTS_BODY" | jq -r '.data[0].min_threshold // empty' 2>/dev/null)"
ALERT_DEFICIT="$(echo "$ALERTS_BODY" | jq -r '.data[0].deficit // empty' 2>/dev/null)"

if [[ -n "$ALERT_PRODUCT_ID" ]]; then
    pass "Alert item has product field (name: $ALERT_PRODUCT_NAME)"
else
    fail "Alert item missing product.id field"
fi

if [[ -n "$ALERT_WAREHOUSE_ID" ]]; then
    pass "Alert item has warehouse field (id: $ALERT_WAREHOUSE_ID)"
else
    fail "Alert item missing warehouse.id field"
fi

if [[ -n "$ALERT_QTY" ]]; then
    pass "Alert item has quantity: $ALERT_QTY"
else
    fail "Alert item missing quantity field"
fi

if [[ -n "$ALERT_THRESHOLD" ]]; then
    pass "Alert item has min_threshold: $ALERT_THRESHOLD"
else
    fail "Alert item missing min_threshold field"
fi

if [[ -n "$ALERT_DEFICIT" && "$ALERT_DEFICIT" -gt "0" ]]; then
    pass "Alert item has deficit: $ALERT_DEFICIT (quantity is $ALERT_QTY, threshold is $ALERT_THRESHOLD)"
else
    fail "Expected deficit > 0 for a low-stock alert, got '${ALERT_DEFICIT}'"
fi

# Verify deficit is computed correctly: deficit = min_threshold - quantity
if [[ -n "$ALERT_QTY" && -n "$ALERT_THRESHOLD" && -n "$ALERT_DEFICIT" ]]; then
    EXPECTED_DEFICIT=$(( ALERT_THRESHOLD - ALERT_QTY ))
    if [[ "$ALERT_DEFICIT" == "$EXPECTED_DEFICIT" ]]; then
        pass "Deficit computed correctly: $ALERT_THRESHOLD - $ALERT_QTY = $ALERT_DEFICIT"
    else
        fail "Deficit calculation wrong: expected $EXPECTED_DEFICIT (threshold-qty), got $ALERT_DEFICIT"
    fi
fi

# ---------------------------------------------------------------------------
# 8. Audit log — GET /api/v1/audit-log with admin auth + filters
# ---------------------------------------------------------------------------

section "8. Audit log — GET /api/v1/audit-log"

# 8a. Admin access — basic retrieval and entry schema
AUDIT_OUT="$TMP/audit_log.txt"
run_curl "$AUDIT_OUT" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/api/v1/audit-log"

AUDIT_STATUS="$(http_status "$AUDIT_OUT")"
if [[ "$AUDIT_STATUS" == "200" ]]; then
    pass "Audit log returns HTTP 200 for admin user"
else
    fail "Expected HTTP 200 for audit log, got $AUDIT_STATUS"
fi

AUDIT_BODY="$(json_body "$AUDIT_OUT")"
AUDIT_TOTAL="$(echo "$AUDIT_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
AUDIT_PAGE="$(echo "$AUDIT_BODY" | jq -r '.pagination.page // empty' 2>/dev/null)"
AUDIT_PER_PAGE="$(echo "$AUDIT_BODY" | jq -r '.pagination.per_page // empty' 2>/dev/null)"

if [[ -n "$AUDIT_TOTAL" && "$AUDIT_TOTAL" -gt "0" ]]; then
    pass "Audit log has $AUDIT_TOTAL entries total"
else
    fail "Expected non-zero audit log total, got '${AUDIT_TOTAL}'"
fi

if [[ -n "$AUDIT_PAGE" && -n "$AUDIT_PER_PAGE" ]]; then
    pass "Audit log pagination envelope present: page=$AUDIT_PAGE, per_page=$AUDIT_PER_PAGE"
else
    fail "Audit log pagination envelope missing page or per_page fields"
fi

# Verify audit entry field schema
AUDIT_ENTRY_ID="$(echo "$AUDIT_BODY" | jq -r '.data[0].id // empty' 2>/dev/null)"
AUDIT_ENTRY_USER_ID="$(echo "$AUDIT_BODY" | jq -r '.data[0].user_id // empty' 2>/dev/null)"
AUDIT_ENTRY_ACTION="$(echo "$AUDIT_BODY" | jq -r '.data[0].action // empty' 2>/dev/null)"
AUDIT_ENTRY_TYPE="$(echo "$AUDIT_BODY" | jq -r '.data[0].resource_type // empty' 2>/dev/null)"
AUDIT_ENTRY_RES_ID="$(echo "$AUDIT_BODY" | jq -r '.data[0].resource_id // empty' 2>/dev/null)"
AUDIT_ENTRY_CHANGES="$(echo "$AUDIT_BODY" | jq -r 'if .data[0].changes != null then "present" else empty end' 2>/dev/null)"
AUDIT_ENTRY_IP="$(echo "$AUDIT_BODY" | jq -r '.data[0].ip_address // empty' 2>/dev/null)"
AUDIT_ENTRY_TS="$(echo "$AUDIT_BODY" | jq -r '.data[0].created_at // empty' 2>/dev/null)"

if [[ -n "$AUDIT_ENTRY_ID" ]]; then
    pass "Audit log entry has id field"
else
    fail "Audit log entry missing id field"
fi

if [[ -n "$AUDIT_ENTRY_USER_ID" ]]; then
    pass "Audit log entry has user_id field"
else
    fail "Audit log entry missing user_id field"
fi

if [[ -n "$AUDIT_ENTRY_ACTION" ]]; then
    pass "Audit log entry has action field: $AUDIT_ENTRY_ACTION"
else
    fail "Audit log entry missing action field"
fi

if [[ -n "$AUDIT_ENTRY_TYPE" ]]; then
    pass "Audit log entry has resource_type field: $AUDIT_ENTRY_TYPE"
else
    fail "Audit log entry missing resource_type field"
fi

if [[ -n "$AUDIT_ENTRY_RES_ID" ]]; then
    pass "Audit log entry has resource_id field"
else
    fail "Audit log entry missing resource_id field"
fi

if [[ "$AUDIT_ENTRY_CHANGES" == "present" ]]; then
    pass "Audit log entry has changes field (non-null)"
else
    fail "Audit log entry missing or null changes field"
fi

if [[ -n "$AUDIT_ENTRY_IP" ]]; then
    pass "Audit log entry has ip_address field: $AUDIT_ENTRY_IP"
else
    fail "Audit log entry missing ip_address field"
fi

if [[ -n "$AUDIT_ENTRY_TS" ]]; then
    pass "Audit log entry has created_at timestamp"
else
    fail "Audit log entry missing created_at field"
fi

# 8b. Filter by action=create
AUDIT_CREATE_OUT="$TMP/audit_create.txt"
run_curl "$AUDIT_CREATE_OUT" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/api/v1/audit-log?action=create"

AUDIT_CREATE_STATUS="$(http_status "$AUDIT_CREATE_OUT")"
if [[ "$AUDIT_CREATE_STATUS" == "200" ]]; then
    pass "Audit log action=create filter returns HTTP 200"
else
    fail "Expected HTTP 200 for audit-log?action=create, got $AUDIT_CREATE_STATUS"
fi

AUDIT_CREATE_BODY="$(json_body "$AUDIT_CREATE_OUT")"
AUDIT_CREATE_TOTAL="$(echo "$AUDIT_CREATE_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
AUDIT_CREATE_FIRST="$(echo "$AUDIT_CREATE_BODY" | jq -r '.data[0].action // empty' 2>/dev/null)"

if [[ -n "$AUDIT_CREATE_TOTAL" && "$AUDIT_CREATE_TOTAL" -gt "0" ]]; then
    pass "Audit action=create filter returned $AUDIT_CREATE_TOTAL create entries"
else
    fail "Expected create-action entries in audit log, got total='${AUDIT_CREATE_TOTAL}'"
fi

if [[ "$AUDIT_CREATE_FIRST" == "create" ]]; then
    pass "Action filter working — first returned entry has action='create'"
else
    fail "Expected first entry action='create', got '${AUDIT_CREATE_FIRST}'"
fi

# 8c. Filter by resource_type=product
AUDIT_PROD_OUT="$TMP/audit_product.txt"
run_curl "$AUDIT_PROD_OUT" \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    "${BASE_URL}/api/v1/audit-log?resource_type=product"

AUDIT_PROD_STATUS="$(http_status "$AUDIT_PROD_OUT")"
if [[ "$AUDIT_PROD_STATUS" == "200" ]]; then
    pass "Audit log resource_type=product filter returns HTTP 200"
else
    fail "Expected HTTP 200 for audit-log?resource_type=product, got $AUDIT_PROD_STATUS"
fi

AUDIT_PROD_BODY="$(json_body "$AUDIT_PROD_OUT")"
AUDIT_PROD_TOTAL="$(echo "$AUDIT_PROD_BODY" | jq -r '.pagination.total // empty' 2>/dev/null)"
AUDIT_PROD_FIRST="$(echo "$AUDIT_PROD_BODY" | jq -r '.data[0].resource_type // empty' 2>/dev/null)"

if [[ -n "$AUDIT_PROD_TOTAL" && "$AUDIT_PROD_TOTAL" -gt "0" ]]; then
    pass "Audit resource_type=product filter returned $AUDIT_PROD_TOTAL product entries"
else
    fail "Expected product resource entries in audit log, got total='${AUDIT_PROD_TOTAL}'"
fi

if [[ "$AUDIT_PROD_FIRST" == "product" ]]; then
    pass "Resource type filter working — first returned entry has resource_type='product'"
else
    fail "Expected first entry resource_type='product', got '${AUDIT_PROD_FIRST}'"
fi

# 8d. Unauthenticated access must return 401 with error envelope
AUDIT_UNAUTH_OUT="$TMP/audit_unauth.txt"
run_curl "$AUDIT_UNAUTH_OUT" "${BASE_URL}/api/v1/audit-log"

AUDIT_UNAUTH_STATUS="$(http_status "$AUDIT_UNAUTH_OUT")"
AUDIT_UNAUTH_BODY="$(json_body "$AUDIT_UNAUTH_OUT")"
AUDIT_UNAUTH_CODE="$(echo "$AUDIT_UNAUTH_BODY" | jq -r '.error.code // empty' 2>/dev/null)"
AUDIT_UNAUTH_MSG="$(echo "$AUDIT_UNAUTH_BODY" | jq -r '.error.message // empty' 2>/dev/null)"

if [[ "$AUDIT_UNAUTH_STATUS" == "401" ]]; then
    pass "Unauthenticated audit log access returns HTTP 401"
else
    fail "Expected HTTP 401 for unauthenticated audit-log, got $AUDIT_UNAUTH_STATUS"
fi

if [[ -n "$AUDIT_UNAUTH_CODE" && -n "$AUDIT_UNAUTH_MSG" ]]; then
    pass "Unauthenticated 401 follows error envelope: code=$AUDIT_UNAUTH_CODE"
else
    fail "Unauthenticated 401 missing error envelope — body: $(echo "$AUDIT_UNAUTH_BODY" | head -c 200)"
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
echo "All business logic smoke tests passed."
exit 0
