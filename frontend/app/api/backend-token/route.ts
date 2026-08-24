import { NextResponse } from "next/server";

import { auth0 } from "@/lib/auth0";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function GET() {
  try {
    const { token: auth0AccessToken } = await auth0.getAccessToken();

    if (!auth0AccessToken) {
      return NextResponse.json(
        { detail: "Not authenticated" },
        { status: 401 }
      );
    }

    const response = await fetch(`${API_BASE_URL}/auth/auth0/login`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${auth0AccessToken}`,
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      return NextResponse.json(
        {
          detail:
            payload.detail ?? "Unable to exchange Auth0 session for backend token",
        },
        { status: response.status }
      );
    }

    const data = await response.json();

    return NextResponse.json(
      {
        backendAccessToken: data.access_token,
        backendRefreshToken: data.refresh_token,
      },
      { status: 200 }
    );
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Unable to exchange Auth0 session for backend token";

    return NextResponse.json(
      { detail: message },
      { status: 401 }
    );
  }
}
