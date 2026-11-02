"""Database entities and repositories for authentication."""

from appkit_user.authentication.backend.database.entities import (
    LoginThrottleEntity,
    OAuthAccountEntity,
    OAuthStateEntity,
    PasswordHistoryEntity,
    PasswordResetRequestEntity,
    PasswordResetTokenEntity,
    UserEntity,
    UserSessionEntity,
)
from appkit_user.authentication.backend.database.login_throttle_repository import (
    LoginThrottleRepository,
    login_throttle_repo,
)
from appkit_user.authentication.backend.database.oauthstate_repository import (
    OAuthStateRepository,
    oauth_state_repo,
)
from appkit_user.authentication.backend.database.password_history_repository import (
    PasswordHistoryRepository,
    password_history_repo,
)
from appkit_user.authentication.backend.database.password_reset_repository import (
    PasswordResetTokenRepository,
    password_reset_token_repo,
)
from appkit_user.authentication.backend.database.password_reset_request_repository import (  # noqa: E501
    PasswordResetRequestRepository,
    password_reset_request_repo,
)
from appkit_user.authentication.backend.database.user_repository import (
    DefaultUserRoles,
    UserRepository,
    user_repo,
)
from appkit_user.authentication.backend.database.user_session_repository import (
    UserSessionRepository,
    session_repo,
)

__all__ = [
    "DefaultUserRoles",
    "LoginThrottleEntity",
    "LoginThrottleRepository",
    "OAuthAccountEntity",
    "OAuthStateEntity",
    "OAuthStateRepository",
    "PasswordHistoryEntity",
    "PasswordHistoryRepository",
    "PasswordResetRequestEntity",
    "PasswordResetRequestRepository",
    "PasswordResetTokenEntity",
    "PasswordResetTokenRepository",
    "UserEntity",
    "UserRepository",
    "UserSessionEntity",
    "UserSessionRepository",
    "login_throttle_repo",
    "oauth_state_repo",
    "password_history_repo",
    "password_reset_request_repo",
    "password_reset_token_repo",
    "session_repo",
    "user_repo",
]
