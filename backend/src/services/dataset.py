import hashlib,json
from datetime import datetime,timezone
from sqlalchemy import select
from fastapi import HTTPException
from ..models.dataset import Dataset
from ..models.segment import DatasetSegment
from ..constants.enums import SEGMENT_MAX_OPERATIONS,RECEIVING,SEALED
def digest(operations):return hashlib.sha256(json.dumps(operations,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def gaps(declared,segments):
    """Return missing [start,end] ranges over the declared 1..declared sequence."""
    covered=set()
    for seg in segments:covered.update(range(seg.start_seq,seg.start_seq+seg.count))
    missing=[];cursor=None
    for seq in range(1,declared+1):
        if seq not in covered:
            if cursor is None:cursor=seq
        elif cursor is not None:
            missing.append([cursor,seq-1]);cursor=None
    if cursor is not None:missing.append([cursor,declared])
    return missing
def segment_dict(x):return {'start_seq':x.start_seq,'count':x.count,'content_hash':x.content_hash}
def canonical(segments):
    """Map seq -> operation across accepted segments; duplicates were verified equal at intake."""
    rows={}
    for seg in segments:
        for offset,entry in enumerate(seg.operations):
            seq=seg.start_seq+offset
            rows.setdefault(seq,{'op':entry['op'],'key':entry['key'],'value':entry.get('value')})
    return rows
def ordered_entries(segments):
    rows=canonical(segments)
    return [rows[seq] for seq in sorted(rows)]
def serialize(x,segments=()):
    segments=list(segments)
    declared=x.total_count
    sealed=x.status==SEALED
    covered=set()
    for s in segments:covered.update(range(s.start_seq,s.start_seq+s.count))
    return {'id':x.id,'name':x.name,'description':x.description,'entries':x.entries,'operation_count':len(x.entries),'distinct_keys':len({e['key'] for e in x.entries}),'status':x.status,'total_count':declared,'sealed_at':str(x.sealed_at) if x.sealed_at else None,'revision':x.revision,'received_count':len(x.entries) if sealed else len(covered),'gaps':[] if sealed or not declared else gaps(declared,segments),'segments':[segment_dict(s) for s in sorted(segments,key=lambda s:s.start_seq)]}
def _segments(db,ident):return list(db.scalars(select(DatasetSegment).where(DatasetSegment.dataset_id==ident).order_by(DatasetSegment.start_seq)))
def _segments_locked(db,ident):return list(db.scalars(select(DatasetSegment).where(DatasetSegment.dataset_id==ident).order_by(DatasetSegment.start_seq, DatasetSegment.id).with_for_update()))
def listing(db):
    rows=list(db.scalars(select(Dataset).order_by(Dataset.id)))
    by={}
    for s in db.scalars(select(DatasetSegment).order_by(DatasetSegment.start_seq)).all():by.setdefault(s.dataset_id,[]).append(s)
    return [serialize(x,by.get(x.id,[])) for x in rows]
def detail(db,ident):
    x=db.get(Dataset,ident)
    if not x:raise HTTPException(404,'写入批次不存在')
    return serialize(x,_segments(db,x.id))
def create(db,data):
    if db.scalar(select(Dataset).where(Dataset.name==data.name)):raise HTTPException(409,'写入批次名称已存在')
    if data.entries:
        total=len(data.entries)
        x=Dataset(name=data.name,description=data.description,entries=[e.model_dump() for e in data.entries],status=SEALED,total_count=total,revision=1,sealed_at=datetime.now(timezone.utc))
        db.add(x);db.commit();return serialize(db.get(Dataset,x.id))
    if data.total_count and data.total_count>SEGMENT_MAX_OPERATIONS:raise HTTPException(422,f'声明总条数不得超过{SEGMENT_MAX_OPERATIONS}')
    x=Dataset(name=data.name,description=data.description,entries=[],status=RECEIVING,total_count=data.total_count,revision=0)
    db.add(x);db.commit();x=db.get(Dataset,x.id)
    return serialize(x)
def _locked(db,ident):
    x=db.scalar(select(Dataset).where(Dataset.id==ident).with_for_update())
    if not x:raise HTTPException(404,'写入批次不存在')
    return x
def append_segment(db,ident,data):
    operations=[e.model_dump() for e in data.operations]
    content=digest(operations)
    x=_locked(db,ident)
    if x.status==SEALED:raise HTTPException(409,'批次已封存，禁止追加分段')
    declared=x.total_count
    if declared is None:raise HTTPException(409,'该批次不是分段补传批次')
    end=data.start_seq+len(operations)-1
    if end>declared:raise HTTPException(422,f'分段越过声明总条数 {declared}，整段拒绝')
    accepted=canonical(_segments_locked(db,x.id))
    incoming={data.start_seq+i:operations[i] for i in range(len(operations))}
    for seq,entry in incoming.items():
        if seq in accepted and accepted[seq]!=entry:raise HTTPException(409,f'分段与已收序号 {seq} 内容冲突，整段拒绝')
    if all(seq in accepted for seq in incoming):
        db.rollback()
        return serialize(db.get(Dataset,ident),_segments(db,ident)),True
    db.add(DatasetSegment(dataset_id=x.id,start_seq=data.start_seq,count=len(operations),operations=operations,content_hash=content))
    x.revision+=1
    db.commit()
    return serialize(db.get(Dataset,ident),_segments(db,ident)),False
def seal(db,ident):
    x=_locked(db,ident)
    if x.status==SEALED:return serialize(x,_segments(db,x.id)),True
    declared=x.total_count
    if not declared:raise HTTPException(409,'批次缺少声明总条数，无法封存')
    if declared>SEGMENT_MAX_OPERATIONS:raise HTTPException(422,'声明总条数超过2000，无法封存')
    segments=_segments_locked(db,x.id)
    missing=gaps(declared,segments)
    if missing:
        raise HTTPException(409,{'detail':'连续序号未补齐，不能封存','gaps':missing,'received':sum(s.count for s in segments),'total':declared})
    entries=ordered_entries(segments)
    if len(entries)!=declared:raise HTTPException(409,'分段拼接后条数与声明不符，封存拒绝')
    x.entries=entries;x.status=SEALED;x.sealed_at=datetime.now(timezone.utc)
    db.commit()
    return serialize(db.get(Dataset,ident),_segments(db,ident)),False
