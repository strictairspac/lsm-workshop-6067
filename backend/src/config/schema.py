from sqlalchemy import inspect,text
from sqlalchemy.exc import SQLAlchemyError
def ensure_schema(engine):
    """Idempotent v1 -> v2 migration: segment receipts and batch lifecycle columns."""
    from ..models.dataset import Dataset
    from ..models.segment import DatasetSegment
    from ..models import audit,config,trial,user  # noqa: F401 - register metadata
    from .database import Base
    Base.metadata.create_all(engine)
    columns={c['name'] for c in inspect(engine).get_columns('datasets')}
    with engine.begin() as conn:
        if 'status' not in columns:
            conn.execute(text('ALTER TABLE datasets ADD COLUMN status VARCHAR(20) NULL'))
        if 'total_count' not in columns:
            conn.execute(text('ALTER TABLE datasets ADD COLUMN total_count INT NULL'))
        if 'sealed_at' not in columns:
            conn.execute(text('ALTER TABLE datasets ADD COLUMN sealed_at DATETIME NULL'))
        if 'revision' not in columns:
            conn.execute(text('ALTER TABLE datasets ADD COLUMN revision INT NOT NULL DEFAULT 0'))
        # Legacy rows already carried a complete, usable operation sequence.
        try:conn.execute(text("UPDATE datasets SET status='sealed', total_count=JSON_LENGTH(entries), revision=0 WHERE status IS NULL OR status=''"))
        except SQLAlchemyError:pass
    trial_columns={c['name'] for c in inspect(engine).get_columns('trials')}
    with engine.begin() as conn:
        if 'claimed_at' not in trial_columns:
            conn.execute(text('ALTER TABLE trials ADD COLUMN claimed_at DATETIME NULL'))
    # Early builds forbade overlapping segments; overlaps are now accepted receipts.
    indexes={i['name'] for i in inspect(engine).get_indexes('dataset_segments')}
    if 'uq_dataset_segment_start' in indexes:
        with engine.begin() as conn:conn.execute(text('ALTER TABLE dataset_segments DROP INDEX uq_dataset_segment_start'))
