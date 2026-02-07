from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health

import base64
import json
from urllib.parse import urlencode
from fastapi import Request
from fastapi.responses import RedirectResponse
import httpx

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }

@app.get("/square/callback")
async def square_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handles Square OAuth callback and redirects to the appropriate client domain.
    """

    if error:
        # Handle user denied or OAuth error
        return RedirectResponse(f"http://localhost:3000?error={error}")

    callback_url = None
    redirect_url_from_state = None
    client_id = "unknown"
    redirect_after = ""
    extra_params = {}


    if state:
        try:
            decoded = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(decoded)
            # New state shape: callbackUrl, redirectUrl, clientId
            callback_url = state_data.get("callbackUrl") or state_data.get("callback_url")
            redirect_url_from_state = state_data.get("redirectUrl") or state_data.get("redirect_url")
            # Support camelCase (from JS) and snake_case
            client_id = state_data.get("clientId") or state_data.get("client_id", "unknown")
            redirect_after = state_data.get("redirectAfter") or state_data.get("redirect_after") or ""
            extra_params = state_data.get("extra", {})
        except Exception as e:
            print(f"[square/callback] Failed to decode state: {e}")


    # New state shape: POST code to callbackUrl, then redirect user to redirectUrl
    if callback_url and redirect_url_from_state:
        if code:
            try:
                # Replace localhost with host.docker.internal for server-to-server calls from Docker
                server_callback_url = callback_url.replace("://localhost", "://host.docker.internal")
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        server_callback_url,
                        json={"code": code},
                        timeout=15.0,
                    )
            except Exception as e:
                print(f"[square/callback] Failed to hit callback URL: {type(e).__name__}: {e}")
        return RedirectResponse(redirect_url_from_state)

    # Fallback: legacy state shape (clientId + redirectAfter / path)
    if client_id == "local":
        domain = "http://host.docker.internal:3000"
    else:
        domain = f"https://{client_id}.pud.digital"
    path = redirect_after if redirect_after.startswith("/") else f"/{redirect_after}" if redirect_after else ""
    params = {"code": code} if code else {}
    params.update(extra_params)
    redirect_url = f"{domain}{path}?{urlencode(params)}"
    return RedirectResponse(redirect_url)