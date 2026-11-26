"""Fase 8: multi-sede con sucursal en productos, movimientos y lotes

Revision ID: b8cf67ebf4ea
Revises: 808ea84ec146
Create Date: 2026-11-26 11:48:38.099527

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8cf67ebf4ea'
down_revision = '808ea84ec146'
branch_labels = None
depends_on = None

TABLAS = (
    ("productos", "ix_productos_sucursal"),
    ("movimientos", "ix_movimientos_sucursal"),
    ("lotes", "ix_lotes_sucursal"),
)


def _sucursal_principal(bind):
    """Devuelve la sucursal base, creándola si la base está vacía."""
    principal = bind.execute(
        sa.text("SELECT id FROM sucursales ORDER BY id LIMIT 1")
    ).scalar()
    if principal is None:
        bind.execute(sa.text(
            "INSERT INTO sucursales (nombre, direccion, telefono, activa, created_at) "
            "VALUES ('Principal', NULL, NULL, 1, CURRENT_TIMESTAMP)"
        ))
        principal = bind.execute(
            sa.text("SELECT id FROM sucursales ORDER BY id LIMIT 1")
        ).scalar()
    return principal


def upgrade():
    bind = op.get_bind()
    principal = _sucursal_principal(bind)

    for tabla, indice in TABLAS:
        op.add_column(tabla, sa.Column("sucursal_id", sa.Integer(), nullable=True))
        bind.execute(
            sa.text("UPDATE %s SET sucursal_id = :sid" % tabla),
            {"sid": principal},
        )
        with op.batch_alter_table(tabla, schema=None) as batch_op:
            batch_op.alter_column("sucursal_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_index(indice, ["sucursal_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_%s_sucursal" % tabla, "sucursales", ["sucursal_id"], ["id"]
            )


def downgrade():
    for tabla, indice in reversed(TABLAS):
        with op.batch_alter_table(tabla, schema=None) as batch_op:
            batch_op.drop_constraint("fk_%s_sucursal" % tabla, type_="foreignkey")
            batch_op.drop_index(indice)
            batch_op.drop_column("sucursal_id")
