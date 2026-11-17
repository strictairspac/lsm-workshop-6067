from fastapi import APIRouter,Depends
from ..config.database import get_db
from ..schemas.dataset import DatasetInput,SegmentInput
from ..services.auth import current_user,writer
from ..services.dataset import listing,create,detail,append_segment,seal
router=APIRouter(prefix='/datasets')
@router.get('')
def get(db=Depends(get_db),user=Depends(current_user)):return listing(db)
@router.post('',status_code=201)
def add(data:DatasetInput,db=Depends(get_db),user=Depends(writer)):return create(db,data)
@router.get('/{ident}')
def one(ident:int,db=Depends(get_db),user=Depends(current_user)):return detail(db,ident)
@router.post('/{ident}/segments',status_code=201)
def add_segment(ident:int,data:SegmentInput,db=Depends(get_db),user=Depends(writer)):
    body,replayed=append_segment(db,ident,data)
    return {'replayed':replayed,**body}
@router.post('/{ident}/seal')
def seal_batch(ident:int,db=Depends(get_db),user=Depends(writer)):
    body,replayed=seal(db,ident)
    return {'sealed':True,'already_sealed':replayed,**body}
