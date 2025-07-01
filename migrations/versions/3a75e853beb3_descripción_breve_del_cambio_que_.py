"""Descripción breve del cambio que quieres hacer

Revision ID: 3a75e853beb3
Revises: cd8c745d7b3c
Create Date: 2025-06-05 09:40:49.281337

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3a75e853beb3'
down_revision = 'cd8c745d7b3c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('detalles_pedido', schema=None) as batch_op:
        batch_op.add_column(sa.Column('producto_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_detalles_pedido_producto_id', 'producto', ['producto_id'], ['id'])


def downgrade():
    with op.batch_alter_table('detalles_pedido', schema=None) as batch_op:
        batch_op.drop_constraint('fk_detalles_pedido_producto_id', type_='foreignkey')
        batch_op.drop_column('producto_id')

    op.create_table(
        '_alembic_tmp_detalles_pedido',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('pedido_id', sa.INTEGER(), nullable=False),
        sa.Column('producto', sa.VARCHAR(length=100), nullable=False),
        sa.Column('precio', sa.FLOAT(), nullable=False),
        sa.Column('cantidad', sa.INTEGER(), nullable=False),
        sa.Column('producto_id', sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id']),
        sa.ForeignKeyConstraint(['producto_id'], ['producto.id'], name=op.f('fk_detalles_producto_id')),
        sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###
