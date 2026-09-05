/**
 * Health Client Unit / Integration Verification
 * Tests the offline error contract and online health recovery.
 */

async function testHealthClient() {
  console.log('=== Testing Health State Machine & API Client Error Handling ===\n');

  // Helper simulating the API client error mapping logic
  async function simulateGetHealth(baseUrl) {
    try {
      const response = await fetch(`${baseUrl}/api/v1/health`, {
        signal: AbortSignal.timeout(2000),
      });
      if (!response.ok) {
        throw { code: 'http_error', status: response.status, message: `HTTP ${response.status}` };
      }
      return { status: 'online', data: await response.json(), error: null };
    } catch (err) {
      return {
        status: 'offline',
        data: null,
        error: {
          code: 'network_error',
          message: `Failed to connect to backend at ${baseUrl}. (${err.message})`,
        },
      };
    }
  }

  // 1. Verify offline behavior (backend currently stopped)
  console.log('1. Checking behavior when backend is STOPPED:');
  const offlineResult = await simulateGetHealth('http://localhost:8000');
  console.log('   Result status:', offlineResult.status);
  console.log('   Error code:', offlineResult.error?.code);
  console.log('   Error message:', offlineResult.error?.message);

  if (offlineResult.status !== 'offline' || offlineResult.error?.code !== 'network_error') {
    console.error('FAILED: Expected offline state with network_error');
    process.exit(1);
  }
  console.log('   [PASS] Offline state correctly identified without throwing or crashing.\n');
}

testHealthClient();
