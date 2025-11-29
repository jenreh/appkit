"""Add hours tracking system with employee bookings, import summaries, and project numbers

Revision ID: 4de8db9a8e68
Revises: 9a8b7c6d5e4f
Create Date: 2025-10-01 11:05:00.000000

This migration consolidates the hours tracking feature:
- Creates hours_employee_booking table for storing employee time bookings
- Creates hours_import_summary table for tracking Excel imports
- Creates hours_project_numbers table for user-specific project numbers
- All tables include user_id for multi-user support with proper foreign keys
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4de8db9a8e68"
down_revision: str | None = "9a8b7c6d5e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all hours tracking tables with final schema."""

    # Step 1: Create ImportStatus enum type if it doesn't exist
    # Use raw SQL to avoid SQLAlchemy's auto-create behavior
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE importstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )
    # Don't commit - let Alembic handle transaction management

    # Step 2: Create hours_employee_booking table
    # This is the final schema with user_id, renamed table, and correct columns
    op.create_table(
        "hours_employee_booking",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("vertragsposition", sa.String(), nullable=False),
        sa.Column("datum", sa.Date(), nullable=False),
        sa.Column("projektbezeichnung", sa.String(), nullable=False),
        sa.Column("unterprojekt", sa.String(), nullable=True),
        sa.Column("ticket", sa.String(), nullable=True),
        sa.Column("erstellungsdatum", sa.Date(), nullable=False),
        sa.Column("nachname", sa.String(), nullable=False),
        sa.Column("person_days", sa.Float(), nullable=False),
        sa.Column("komment", sa.String(), nullable=True),
        # Foreign key to auth_users
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_hours_employee_booking_user_id",
            ondelete="CASCADE",
        ),
        # Final unique constraint including user_id and correct columns
        sa.UniqueConstraint(
            "user_id",
            "vertragsposition",
            "datum",
            "unterprojekt",
            "nachname",
            "person_days",
            "komment",
            name="uq_hours_employee_booking_record",
        ),
    )

    # Step 3: Create indexes for hours_employee_booking
    op.create_index(
        "ix_hours_employee_booking_datum",
        "hours_employee_booking",
        ["datum"],
    )
    op.create_index(
        "ix_hours_employee_booking_nachname",
        "hours_employee_booking",
        ["nachname"],
    )
    op.create_index(
        "ix_hours_employee_booking_user_id",
        "hours_employee_booking",
        ["user_id"],
    )

    # Step 4: Create hours_import_summary table
    # This is the final schema with DateTime (not Date), user_id, and renamed table
    op.create_table(
        "hours_import_summary",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column(
            "import_date", sa.DateTime(), nullable=False
        ),  # DateTime from the start
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                name="importstatus",
                create_type=False,  # Don't auto-create, we handle it explicitly
            ),
            nullable=False,
        ),
        sa.Column("new_records", sa.Integer(), nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False),
        sa.Column("records_updated", sa.Integer(), nullable=False),
        sa.Column("total_rows_processed", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        # Foreign key to auth_users
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_hours_import_summary_user_id",
            ondelete="CASCADE",
        ),
    )

    # Step 5: Create indexes for hours_import_summary
    op.create_index(
        "ix_hours_import_summary_import_date",
        "hours_import_summary",
        ["import_date"],
    )
    op.create_index(
        "ix_hours_import_summary_user_id",
        "hours_import_summary",
        ["user_id"],
    )

    # Step 6: Create hours_project_numbers table
    op.create_table(
        "hours_project_numbers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("project_number", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # Foreign key to auth_users
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth_users.id"],
            name="fk_hours_project_numbers_user_id",
            ondelete="CASCADE",
        ),
        # Composite unique constraint to prevent duplicate project numbers per user
        sa.UniqueConstraint(
            "user_id",
            "project_number",
            name="uq_hours_project_number_per_user",
        ),
    )

    # Step 7: Create index for hours_project_numbers
    op.create_index(
        "ix_hours_project_numbers_user_id",
        "hours_project_numbers",
        ["user_id"],
    )


def downgrade() -> None:
    """Drop all hours tracking tables and enum."""

    # Drop tables in reverse dependency order
    op.drop_table("hours_project_numbers")
    op.drop_table("hours_import_summary")
    op.drop_table("hours_employee_booking")

    # Drop the enum type using raw SQL
    # The CASCADE ensures it's dropped even if there are dependencies
    conn = op.get_bind()
    conn.execute(sa.text("DROP TYPE IF EXISTS importstatus CASCADE"))
    # Don't commit - let Alembic handle transaction management
