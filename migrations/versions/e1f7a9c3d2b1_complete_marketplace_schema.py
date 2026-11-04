"""Complete marketplace schema

Revision ID: e1f7a9c3d2b1
Revises: bd5c1879f504
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f7a9c3d2b1"
down_revision = "bd5c1879f504"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("skill", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requirements", sa.Text(), nullable=True))

    with op.batch_alter_table("demand", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requirements", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "urgency",
                sa.String(length=16),
                nullable=False,
                server_default="medium",
            )
        )
        batch_op.add_column(sa.Column("deadline", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_demand_urgency", ["urgency"], unique=False)

    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("demand_id", sa.Integer(), nullable=True),
        sa.Column("transaction_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=64),
            nullable=False,
            server_default="pending_approval",
        ),
        sa.Column("agreed_terms", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["demand_id"], ["demand.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["requester_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skill.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("transaction", schema=None) as batch_op:
        batch_op.create_index("ix_transaction_demand_id", ["demand_id"], unique=False)
        batch_op.create_index("ix_transaction_item_id", ["item_id"], unique=False)
        batch_op.create_index("ix_transaction_provider_id", ["provider_id"], unique=False)
        batch_op.create_index("ix_transaction_requester_id", ["requester_id"], unique=False)
        batch_op.create_index("ix_transaction_skill_id", ["skill_id"], unique=False)
        batch_op.create_index("ix_transaction_status", ["status"], unique=False)
        batch_op.create_index(
            "ix_transaction_transaction_type",
            ["transaction_type"],
            unique=False,
        )

    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=False),
        sa.Column("reviewee_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reply", sa.Text(), nullable=True),
        sa.Column("replied_at", sa.DateTime(), nullable=True),
        sa.Column("review_type", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reviewee_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transaction.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transaction_id",
            "reviewer_id",
            name="uq_review_transaction_reviewer",
        ),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )
    with op.batch_alter_table("review", schema=None) as batch_op:
        batch_op.create_index("ix_review_reviewee_id", ["reviewee_id"], unique=False)
        batch_op.create_index("ix_review_reviewer_id", ["reviewer_id"], unique=False)
        batch_op.create_index("ix_review_transaction_id", ["transaction_id"], unique=False)


def downgrade():
    op.drop_table("review")
    op.drop_table("transaction")
    with op.batch_alter_table("demand", schema=None) as batch_op:
        batch_op.drop_index("ix_demand_urgency")
        batch_op.drop_column("deadline")
        batch_op.drop_column("urgency")
        batch_op.drop_column("requirements")
    with op.batch_alter_table("skill", schema=None) as batch_op:
        batch_op.drop_column("requirements")
