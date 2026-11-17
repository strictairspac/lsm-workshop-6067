from datetime import datetime
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,ForeignKey,DateTime,func
from ..config.database import Base
class DatasetSegment(Base):
    __tablename__='dataset_segments'
    id:Mapped[int]=mapped_column(primary_key=True)
    dataset_id:Mapped[int]=mapped_column(ForeignKey('datasets.id'),index=True)
    start_seq:Mapped[int]
    count:Mapped[int]
    operations:Mapped[list]=mapped_column(JSON)
    content_hash:Mapped[str]=mapped_column(String(64),index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
