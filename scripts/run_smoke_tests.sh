#!/bin/bash
# Strict mode: exit on error and treat unset variables as errors
set -euo pipefail

# -----------------------------------------------------------------------
# run_smoke_tests.sh
# Verifies that all Flask endpoints are behaving as expected after deployment.
# Smoke tests are run immediately after deploy_ec2.sh to confirm the
# application is in a valid state before starting observability experiments.
# A non-zero exit is returned if any required condition fails,
# which makes this script suitable for use in a CI/CD pipeline check.
# -----------------------------------------------------------------------

# Base URL is read from the first command-line argument
# so the same script works against any EC2 instance without editing
if [ -z "${1:-}" ]; then
    echo "Usage: bash run_smoke_tests.sh <base_url>"
    echo "Example: bash run_smoke_tests.sh http://<EC2_PUBLIC_IP>:5000"
    exit 1
fi

BASE_URL="$1"
# Track whether any test has failed so we can report at the end
FAILED=0

echo "=== Running smoke tests against $BASE_URL ==="

# -----------------------------------------------------------------------
# Helper function: check_status
# Sends a GET request and verifies the HTTP status code matches expected.
# curl's -o /dev/null discards the response body since we only need the code.
# -----------------------------------------------------------------------
check_status() {
    local endpoint="$1"
    local expected_status="$2"
    local description="$3"

    actual_status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint")

    if [ "$actual_status" == "$expected_status" ]; then
        echo "  PASS: $description (status=$actual_status)"
    else
        echo "  FAIL: $description (expected=$expected_status, got=$actual_status)"
        # Increment failure counter rather than exiting immediately
        # so all test results are visible before the script exits
        FAILED=$((FAILED + 1))
    fi
}

# -----------------------------------------------------------------------
# Test 1: Root endpoint must return 200
# Confirms the application is running and reachable on the expected port
# -----------------------------------------------------------------------
check_status "/" "200" "Root endpoint returns 200"

# -----------------------------------------------------------------------
# Test 2: Health endpoint must return 200
# Confirms the dedicated health check is available for monitoring systems
# -----------------------------------------------------------------------
check_status "/health" "200" "Health endpoint returns 200"

# -----------------------------------------------------------------------
# Test 3: Error trigger endpoint must return 500
# Confirms that fault injection is working and errors are observable
# -----------------------------------------------------------------------
check_status "/trigger-error" "500" "Trigger-error endpoint returns 500"

# -----------------------------------------------------------------------
# Test 4: Slow endpoint must return 200 within an acceptable latency window
# The endpoint deliberately delays ~5 seconds, so we allow 4.5–8 seconds.
# We measure latency using curl's time_total variable rather than shell timing
# to keep the measurement as close to the HTTP round-trip as possible.
# -----------------------------------------------------------------------
echo ""
echo "  Testing /slow endpoint (expect ~5s response time)..."

slow_response=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" "$BASE_URL/slow")
slow_status=$(echo "$slow_response" | awk '{print $1}')
slow_time=$(echo "$slow_response" | awk '{print $2}')

# Use awk for floating-point comparison since bash does not support it natively
in_window=$(awk "BEGIN { print ($slow_time >= 4.5 && $slow_time <= 8.0) ? 1 : 0 }")

if [ "$slow_status" == "200" ] && [ "$in_window" == "1" ]; then
    echo "  PASS: Slow endpoint returned 200 in ${slow_time}s (within 4.5–8.0s window)"
else
    echo "  FAIL: Slow endpoint — status=$slow_status, time=${slow_time}s (expected 200 in 4.5–8.0s)"
    FAILED=$((FAILED + 1))
fi

# -----------------------------------------------------------------------
# Test 5: Unstable endpoint must return either 200 or 500
# This endpoint randomly returns either status, so both are valid outcomes.
# The test confirms the endpoint is reachable and responding,
# not that it returns a specific code.
# -----------------------------------------------------------------------
unstable_status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/unstable")

if [ "$unstable_status" == "200" ] || [ "$unstable_status" == "500" ]; then
    echo "  PASS: Unstable endpoint returned acceptable status ($unstable_status)"
else
    echo "  FAIL: Unstable endpoint returned unexpected status ($unstable_status)"
    FAILED=$((FAILED + 1))
fi

# -----------------------------------------------------------------------
# Final result
# Exit with a non-zero code if any test failed so the caller can detect it
# -----------------------------------------------------------------------
echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "=== All smoke tests passed. Application is ready for observability experiments. ==="
    exit 0
else
    echo "=== $FAILED smoke test(s) failed. Review output above before proceeding. ==="
    exit 1
fi