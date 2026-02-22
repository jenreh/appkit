"""Authentication backend services."""

from appkit_user.authentication.backend.services.email_service import (
    AzureEmailProvider,
    EmailProviderBase,
    EmailServiceFactory,
    MockEmailProvider,
    ResendEmailProvider,
    get_email_service,
)
from appkit_user.authentication.backend.services.oauth_service import (
    OAuthService,
    generate_pkce_pair,
)
from appkit_user.authentication.backend.services.session_cleanup_service import (
    SessionCleanupService,
)

__all__ = [
    "AzureEmailProvider",
    "EmailProviderBase",
    "EmailServiceFactory",
    "MockEmailProvider",
    "OAuthService",
    "ResendEmailProvider",
    "SessionCleanupService",
    "generate_pkce_pair",
    "get_email_service",
]
