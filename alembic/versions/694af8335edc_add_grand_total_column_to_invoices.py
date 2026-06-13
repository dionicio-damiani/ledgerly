"""add grand_total column to invoices

Revision ID: 694af8335edc
Revises: b7b5978fbd98
Create Date: 2026-06-13 05:46:30.867986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '694af8335edc'
down_revision: Union[str, Sequence[str], None] = 'b7b5978fbd98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: add the column as nullable so existing rows don't break the DDL.
    op.add_column('invoices', sa.Column('grand_total', sa.Numeric(precision=12, scale=2), nullable=True))

    # Step 2: backfill grand_total for existing rows from their invoice_data.
    from app.models import InvoiceRequest
    from app.services.totals import compute_totals

    connection = op.get_bind()
    invoices = connection.execute(sa.text("SELECT id, invoice_data FROM invoices")).fetchall()

    for inv in invoices:
        payload = InvoiceRequest(**inv.invoice_data)
        totals = compute_totals(payload)
        connection.execute(
            sa.text("UPDATE invoices SET grand_total = :gt WHERE id = :id"),
            {"gt": totals.grand_total, "id": inv.id},
        )

    # Step 3: now that every row has a value, enforce NOT NULL.
    op.alter_column('invoices', 'grand_total', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoices', 'grand_total')
