import hmac
import os
from dataclasses import dataclass

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


@dataclass(frozen=True)
class WorkspaceUser:
    is_authenticated: bool = True
    name: str = "workspace-reviewer"


class WorkspaceAuthentication(BaseAuthentication):
    """A single private showcase workspace. Replace with OIDC before multi-tenancy."""

    def authenticate(self, request):
        expected = os.environ.get("RELAY_API_TOKEN", "")
        supplied = request.headers.get("Authorization", "")
        if not expected or not hmac.compare_digest(supplied, f"Bearer {expected}"):
            raise AuthenticationFailed("A valid workspace token is required.")
        return WorkspaceUser(), None

    def authenticate_header(self, request):
        return "Bearer"
