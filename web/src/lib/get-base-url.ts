/**
 * Returns the base URL for server-side fetch calls to THIS deployment's own
 * API routes.
 *
 * VERCEL_URL (the current deployment) must win over the production domain —
 * otherwise every preview deployment silently calls PRODUCTION code and no
 * API change can ever be preview-tested.
 */
export function getBaseUrl(): string {
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }
  if (process.env.NEXT_PUBLIC_BASE_URL) {
    return process.env.NEXT_PUBLIC_BASE_URL;
  }
  return `http://localhost:${process.env.PORT ?? 3000}`;
}
