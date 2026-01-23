from urllib.parse import parse_qs
import logging

from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()

        existing_user = scope.get("user")
        if existing_user and getattr(existing_user, "is_authenticated", False):
            return await self.inner(scope, receive, send)

        token = None
        query_string = scope.get("query_string", b"").decode()
        if query_string:
            params = parse_qs(query_string)
            token = (params.get("token") or [None])[0]

        if not token:
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            auth_header = headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated = jwt_auth.get_validated_token(token)
                scope["user"] = jwt_auth.get_user(validated)
                logger.info("WS auth ok user_id=%s path=%s", scope["user"].id, scope.get("path"))
            except Exception as exc:
                scope["user"] = AnonymousUser()
                logger.warning("WS auth failed path=%s err=%s", scope.get("path"), exc)
        else:
            logger.warning("WS missing token path=%s", scope.get("path"))

        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack

    return AuthMiddlewareStack(JwtAuthMiddleware(inner))
