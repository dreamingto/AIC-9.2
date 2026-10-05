"""Allow baseline and pinned neural vectors to coexist without replacing one another."""

from alembic import op
import sqlalchemy as sa

revision = "0002_model_spaces"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_embedding_entity_modality", table_name="embedding_records")
    op.create_index(
        "ix_embedding_entity_modality", "embedding_records",
        ["entity_type", "entity_id", "modality"], unique=False,
    )
    op.create_index(
        "ix_embedding_model_space", "embedding_records",
        ["entity_type", "entity_id", "modality", "provider", "model", "version",
         "dimension", "preprocessing_hash"], unique=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    multiple_spaces = connection.execute(sa.text(
        "SELECT 1 FROM embedding_records GROUP BY entity_type, entity_id, modality "
        "HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if multiple_spaces:
        raise RuntimeError(
            "Cannot downgrade while multiple model spaces coexist. "
            "Choose and back up the spaces to retain; migration never deletes vectors."
        )
    op.drop_index("ix_embedding_model_space", table_name="embedding_records")
    op.drop_index("ix_embedding_entity_modality", table_name="embedding_records")
    op.create_index(
        "ix_embedding_entity_modality", "embedding_records",
        ["entity_type", "entity_id", "modality"], unique=True,
    )
