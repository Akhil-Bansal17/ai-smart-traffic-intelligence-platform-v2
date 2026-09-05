/**
 * Frontend Integration and Unit Verification Script
 * Tests the API client error parsing, real HTTP integration with backend,
 * and offline/error state handling.
 */

async function runTests() {
  console.log('=== Starting Frontend Foundation Integration Tests ===\n');

  let passed = 0;
  let failed = 0;

  function assert(condition, message) {
    if (condition) {
      console.log(`  [PASS] ${message}`);
      passed++;
    } else {
      console.error(`  [FAIL] ${message}`);
      failed++;
    }
  }

  const BASE_URL = 'http://localhost:8000';

  // Test 1: GET /api/v1/health (Live backend)
  try {
    const res = await fetch(`${BASE_URL}/api/v1/health`);
    const data = await res.json();
    assert(res.status === 200, 'GET /api/v1/health returned HTTP 200');
    assert(data.status === 'ok', 'Health status is "ok"');
    assert(data.environment === 'development', 'Health environment is "development"');
    assert(data.version === '0.1.0', 'Health version is "0.1.0"');
  } catch (err) {
    assert(false, `Live backend test failed: ${err.message}`);
  }

  // Test 2: GET /health root liveness
  try {
    const res = await fetch(`${BASE_URL}/health`);
    const data = await res.json();
    assert(res.status === 200, 'GET /health returned HTTP 200');
    assert(data.status === 'ok', 'Root health status is "ok"');
    assert(data.service === 'traffic-platform-api', 'Root service name matches');
  } catch (err) {
    assert(false, `Root health test failed: ${err.message}`);
  }

  // Test 3: Centralized 404 Error Format parsing
  try {
    const res = await fetch(`${BASE_URL}/api/v1/nonexistent_endpoint`);
    const data = await res.json();
    assert(res.status === 404, 'Nonexistent endpoint returned HTTP 404');
    assert(data && data.error && typeof data.error === 'object', 'Response contains centralized error object');
    assert(data.error.code === 'http_error', `Error code matches "http_error" (got: ${data?.error?.code})`);
    assert(data.error.message === 'Not Found', `Error message matches "Not Found" (got: ${data?.error?.message})`);
  } catch (err) {
    assert(false, `404 error test failed: ${err.message}`);
  }

  // Test 4: Offline / Unreachable backend simulation (port 9999)
  try {
    await fetch('http://localhost:9999/api/v1/health', { signal: AbortSignal.timeout(1000) });
    assert(false, 'Unreachable backend should throw an exception');
  } catch (err) {
    assert(true, `Unreachable backend correctly caught: ${err.name} (${err.message})`);
  }

  // Test 5: Vite Dev Server is up and serving HTML
  try {
    const res = await fetch('http://localhost:5173/');
    const text = await res.text();
    assert(res.status === 200, 'Vite dev server returned HTTP 200');
    assert(text.includes('AI Smart Traffic Intelligence Platform'), 'HTML contains expected page title');
    assert(text.includes('/src/main.tsx'), 'HTML entry point references /src/main.tsx');
  } catch (err) {
    assert(false, `Vite dev server test failed: ${err.message}`);
  }

  // Test 6: GET /api/v1/videos
  try {
    const res = await fetch(`${BASE_URL}/api/v1/videos`);
    const data = await res.json();
    assert(res.status === 200, 'GET /api/v1/videos returned HTTP 200');
    assert(typeof data.total === 'number', 'Video list has numeric total');
    assert(Array.isArray(data.videos), 'Video list contains videos array');
  } catch (err) {
    assert(false, `Video list test failed: ${err.message}`);
  }

  // Test 7: GET /api/v1/videos/{invalid_id} returns 404 with structured error
  try {
    const res = await fetch(`${BASE_URL}/api/v1/videos/00000000-0000-0000-0000-000000000000`);
    const data = await res.json();
    assert(res.status === 404, 'Nonexistent video returned HTTP 404');
    assert(data.error?.code === 'video_not_found', `Error code matches "video_not_found" (got: ${data?.error?.code})`);
  } catch (err) {
    assert(false, `Video 404 test failed: ${err.message}`);
  }

  console.log(`\n=== Test Summary: ${passed} Passed, ${failed} Failed ===`);
  if (failed > 0) {
    process.exit(1);
  }
}

runTests();
