// k6 smoke / load script for the Frontdesk API.
// Run: k6 run loadtest/k6_smoke.js   (see loadtest/README.md for options)
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const VUS = parseInt(__ENV.VUS || "1", 10);
const DURATION = __ENV.DURATION || "30s";

const errorRate = new Rate("errors");

export const options = {
  vus: VUS,
  duration: DURATION,
  thresholds: {
    // Tune these to your SLOs.
    http_req_duration: ["p(95)<800"], // 95% of requests under 800ms
    errors: ["rate<0.01"], // < 1% application errors
  },
};

function registerOwner() {
  const slug = `lt-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
  const res = http.post(
    `${BASE_URL}/api/v1/auth/register`,
    JSON.stringify({
      email: `${slug}@loadtest.local`,
      password: "supersecure123",
      full_name: "Load Test",
      tenant_name: `LT ${slug}`,
      tenant_slug: slug,
    }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(res, { "register 201": (r) => r.status === 201 });
  errorRate.add(res.status !== 201);
  return res.status === 201 ? res.json("access_token") : null;
}

export default function () {
  const token = registerOwner();
  if (!token) {
    sleep(1);
    return;
  }
  const params = { headers: { Authorization: `Bearer ${token}` } };

  for (const path of ["/api/v1/auth/me", "/api/v1/conversations", "/api/v1/documents", "/api/v1/invitations"]) {
    const res = http.get(`${BASE_URL}${path}`, params);
    check(res, { [`GET ${path} ok`]: (r) => r.status === 200 });
    errorRate.add(res.status >= 400);
  }
  sleep(1);
}
