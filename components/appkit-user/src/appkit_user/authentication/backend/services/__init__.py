"""Authentication backend services."""

from appkit_user.authentication.backend.services.approval_notification import (
    notify_admins_of_pending_user,
    schedule_pending_user_notification,
)
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
from appkit_user.authentication.backend.services.password_reset_service import (
    ChangePasswordOutcome,
    ConfirmResetOutcome,
    ConfirmResetResult,
    PasswordResetService,
    RequestResetOutcome,
    get_password_reset_service,
)
from appkit_user.authentication.backend.services.session_cleanup_service import (
    SessionCleanupService,
)

__all__ = [
    "AzureEmailProvider",
    "ChangePasswordOutcome",
    "ConfirmResetOutcome",
    "ConfirmResetResult",
    "EmailProviderBase",
    "EmailServiceFactory",
    "MockEmailProvider",
    "OAuthService",
    "PasswordResetService",
    "RequestResetOutcome",
    "ResendEmailProvider",
    "SessionCleanupService",
    "generate_pkce_pair",
    "get_email_service",
    "get_password_reset_service",
    "notify_admins_of_pending_user",
    "schedule_pending_user_notification",
]
