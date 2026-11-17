from datetime import datetime
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,DateTime
from ..config.database import Base
from ..constants.enums import RECEIVING
class Dataset(Base):
    __tablename__='datasets'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]=mapped_column(String(120),unique=True)
    description:Mapped[str]=mapped_column(String(2000))
    entries:Mapped[list]=mapped_column(JSON)
    status:Mapped[str]=mapped_column(String(20),default=RECEIVING,server_default=RECEIVING)
    total_count:Mapped[int|None]=mapped_column(nullable=True)
    sealed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    revision:Mapped[int]=mapped_column(default=0,server_default='0')
