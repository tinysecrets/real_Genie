// Optional PostHog analytics, off by default.
//
// Ember surfaces private conversation data, so session recording is never
// enabled. To turn on basic product analytics, build with:
//   REACT_APP_POSTHOG_ENABLED=true
// (and set REACT_APP_POSTHOG_KEY to your project token). The loading stub in
// index.html stays inert until init is called from here.

const POSTHOG_ENABLED = process.env.REACT_APP_POSTHOG_ENABLED === "true";
const POSTHOG_KEY = process.env.REACT_APP_POSTHOG_KEY || "phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs";

export function initAnalytics() {
  if (!POSTHOG_ENABLED || typeof window === "undefined" || !window.posthog) return;
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") return;

  window.posthog.init(POSTHOG_KEY, {
    api_host: process.env.REACT_APP_POSTHOG_HOST || "https://us.i.posthog.com",
    person_profiles: "identified_only",
  });
}