from fastapi import Request
from fastapi.responses import JSONResponse
from proxy.settings import settings

PUBLIC_ROUTES = {"/health", "/metrics"}


async def api_key_middleware(request: Request, call_next):
    """
    Check Authorization: Bearer <PROXY_API_KEY> on every request.
    If PROXY_API_KEY is not set in .env, auth is disabled (dev mode).
    Public routes (/health, /metrics) are always accessible.
    """
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    # Dev mode — no key configured, allow everything
    if not settings.proxy_api_key:
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Missing Authorization header. Include: Authorization: Bearer <your-proxy-key>",
                    "type": "authentication_required",
                    "code": 401,
                }
            },
        )

    provided_key = auth_header[len("Bearer "):]

    if provided_key != settings.proxy_api_key:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Invalid proxy API key.",
                    "type": "invalid_api_key",
                    "code": 401,
                }
            },
        )

    return await call_next(request)
