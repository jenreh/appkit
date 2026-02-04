"""user_manager

Revision ID: 9beec6124919
Revises: 5beb0946474a
Create Date: 2025-06-11 23:30:43.380276

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine

from alembic import op
from app import configuration

# revision identifiers, used by Alembic.
revision: str = "9beec6124919"
down_revision: str | None = "8bcdef012345"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def get_encryption_key() -> str:
    """Get encryption key from environment or config."""
    config = configuration.app.database
    return str(config.encryption_key.get_secret_value())


def upgrade() -> None:
    # Get the encryption key inside the function to avoid import issues
    encryption_key = get_encryption_key()

    op.drop_table("oauth_access_token")
    op.drop_table("oauth_account")
    op.drop_table("oauth_user")
    op.drop_table("referenceteammemberlink")
    op.drop_table("referencetechnologylink")
    op.drop_table("referencetaglink")
    op.drop_table("language")
    op.drop_table("education")
    op.drop_table("workexperience")
    op.drop_table("projectreference")
    op.drop_table("profile")
    op.drop_table("technology")
    op.drop_table("tag")

    # Drop enums
    sa.Enum(name="proficiency").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="ciuenum").drop(op.get_bind(), checkfirst=True)

    # Create the users table
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=200), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("avatar_url", sa.String(length=1500), nullable=True),
        sa.Column("_password", sa.String(length=200), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True, default=False),
        sa.Column("is_admin", sa.Boolean(), nullable=True, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.Column("needs_password_reset", sa.Boolean(), nullable=True, default=False),
        sa.Column(
            "roles",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("session_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.Column(
            "created",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated",
            postgresql.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["auth_users.id"], name="fk_auth_sessions_user_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
        sa.UniqueConstraint("session_id", name="uq_user_sessions_session_id"),
    )

    # Create the users_oauth_accounts table
    op.create_table(
        "auth_oauth_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("auth_users.id"), nullable=False
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("account_id", sa.String(length=100), nullable=False),
        sa.Column("account_email", sa.String(length=200), nullable=False),
        sa.Column(
            "access_token",
            StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
            nullable=False,
        ),
        sa.Column(
            "refresh_token",
            StringEncryptedType(sa.Unicode(), encryption_key, FernetEngine),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("token_type", sa.String(length=20), default="Bearer"),
        sa.Column("scope", sa.String(length=500), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "account_id", name="uq_oauth_provider_account"),
        sa.Index("ix_oauth_accounts_user_id", "user_id"),
    )

    # Create the oauth_states table
    op.create_table(
        "auth_oauth_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("auth_users.id"), nullable=True
        ),
        sa.Column("session_id", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=200), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Index("ix_oauth_states_expires_at", "expires_at"),
    )

    op.execute(
        """
        INSERT INTO public.auth_users
        (email, name, avatar_url, is_active, is_admin, is_verified, _password, created, updated, last_login, needs_password_reset, roles)
        VALUES(
            'admin@aila-solutions.com',
            'Admin Account',
            '',
            true,
            true,
            true,
            'scrypt:32768:8:1$bIA8HVQhPyudwZyV$76d044d2322d395a3a9c95b29337c0c4d24e2426d86d246cc72095fe2455be0540590ecea3c4d433262ea9d9aaa44eaa285363eed568451895ef25652911a2dc',
            '2025-02-03 10:18:40.258',
            '2025-02-03 10:19:14.354',
            '2025-02-03 10:19:14.354',
            false,
            '{"user"}'
        );
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM public.auth_users WHERE email = 'admin@aila-solutions.com';"
    )

    op.drop_table("auth_oauth_states")
    op.drop_table("auth_oauth_accounts")
    op.drop_table("auth_sessions")
    op.drop_table("auth_users")
