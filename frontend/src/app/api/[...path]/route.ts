/**
 * Same-origin reverse proxy for the API. Runs per request, so `API_PROXY_TARGET`
 * is read at container runtime (a Next `rewrites()` rule bakes its target at
 * build time and cannot). Streams responses through unchanged, so SSE on
 * `/api/v1/runs/{id}/events` keeps working.
 */
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const TARGET = (process.env.API_PROXY_TARGET || "http://localhost:8000").replace(/\/$/, "");

async function proxy(req: NextRequest, ctx: { params: { path: string[] } }): Promise<Response> {
  const search = new URL(req.url).search;
  const target = `${TARGET}/api/${ctx.params.path.join("/")}${search}`;

  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers,
    body: hasBody ? req.body : undefined,
    redirect: "manual",
    cache: "no-store",
  };
  if (hasBody) init.duplex = "half";

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return Response.json(
      { error: { code: "upstream_unreachable", message: "the API is not reachable" } },
      { status: 502 },
    );
  }

  const out = new Headers();
  upstream.headers.forEach((value, key) => {
    if (key === "content-encoding" || key === "content-length" || key === "set-cookie") return;
    out.set(key, value);
  });
  const setCookies =
    typeof upstream.headers.getSetCookie === "function" ? upstream.headers.getSetCookie() : [];
  for (const cookie of setCookies) out.append("set-cookie", cookie);

  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const HEAD = proxy;
export const OPTIONS = proxy;
