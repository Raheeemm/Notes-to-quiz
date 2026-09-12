import os

from clerk_backend_api import Clerk
from dotenv import load_dotenv
from fastapi import HTTPException, Request

# The SDK moved this class between releases. Try both known locations.
try:
    from clerk_backend_api.security.types import AuthenticateRequestOptions
except ModuleNotFoundError:
    from clerk_backend_api.jwks_helpers import AuthenticateRequestOptions

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_JWT_KEY = os.getenv("CLERK_JWT_KEY")

if not CLERK_SECRET_KEY:
    raise RuntimeError("CLERK_SECRET_KEY is not set. Check your .env file.")

clerk = Clerk(bearer_auth=CLERK_SECRET_KEY)

# Which frontends are allowed to present tokens to this backend.
AUTHORIZED_PARTIES = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]


def _build_options() -> AuthenticateRequestOptions:
    """Pass jwt_key only when we actually have one.

    With it, verification is a local signature check. Without it, the SDK
    falls back to fetching Clerk's JWKS over the network — slower, but correct.
    """
    kwargs = {"authorized_parties": AUTHORIZED_PARTIES}
    if CLERK_JWT_KEY:
        kwargs["jwt_key"] = CLERK_JWT_KEY
    try:
        return AuthenticateRequestOptions(**kwargs)
    except TypeError:
        # Older SDKs don't accept jwt_key at all.
        return AuthenticateRequestOptions(authorized_parties=AUTHORIZED_PARTIES)


def get_current_user(request: Request) -> str:
    """Verify the Clerk session token and return the Clerk user ID.

    Used as a FastAPI dependency, so any route that declares it is
    automatically protected.
    """
    try:
        state = clerk.authenticate_request(request, _build_options())
    except HTTPException:
        raise
    except Exception as exc:
        # Clerk unreachable, malformed key, etc. Not the caller's fault.
        raise HTTPException(status_code=503, detail=f"Auth service error: {exc}")

    if not state.is_signed_in:
        raise HTTPException(status_code=401, detail=str(state.reason))

    payload = state.payload or {}
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token has no subject claim.")

    return user_id