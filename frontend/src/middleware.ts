import { NextResponse, type NextRequest } from "next/server";

const APP_PREFIXES = ["/dashboard", "/profiles", "/runs", "/matches", "/settings"];
const AUTH_PAGES = ["/login", "/signup"];
const REFRESH_COOKIE = "recruit_refresh";

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const hasSession = req.cookies.has(REFRESH_COOKIE);

  if (APP_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/")) && !hasSession) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // Only bounce to /dashboard when the cookie looks usable. A `next` param means
  // the client guard just sent the user here because its session is dead, so
  // don't ping-pong them back into the app.
  if (AUTH_PAGES.includes(pathname) && hasSession && !req.nextUrl.searchParams.has("next")) {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
