from typing import Literal
from pydantic import BaseModel,Field,model_validator
class Entry(BaseModel):
    op:Literal['put','delete']
    key:str=Field(min_length=1,max_length=64)
    value:str|None=Field(default=None,max_length=200)
    @model_validator(mode='after')
    def check_value(self):
        if self.op=='put' and self.value is None:raise ValueError('put 操作必须包含字符串 value')
        return self
class SegmentInput(BaseModel):
    start_seq:int=Field(ge=1,le=2000)
    count:int|None=Field(default=None,ge=1,le=2000)
    operations:list[Entry]=Field(min_length=1,max_length=2000)
    @model_validator(mode='after')
    def check_count(self):
        if self.count is not None and self.count!=len(self.operations):raise ValueError('count 必须等于 operations 条数')
        return self
class DatasetInput(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    description:str=Field(max_length=2000)
    total_count:int|None=Field(default=None,ge=1,le=2000)
    entries:list[Entry]=Field(default_factory=list,max_length=2000)
    @model_validator(mode='after')
    def check_mode(self):
        if self.entries:
            if self.total_count is not None and self.total_count!=len(self.entries):raise ValueError('total_count 必须等于 entries 条数')
        elif self.total_count is None:
            raise ValueError('分段补传批次必须声明 total_count；完整登记请提供 entries')
        return self
