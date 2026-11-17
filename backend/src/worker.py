import os,time,json,traceback
from datetime import datetime,timedelta,timezone
from pathlib import Path
from sqlalchemy import select,update
from .config.database import Session
from .models.trial import Trial
from .models.dataset import Dataset
from .models.config import Config
from .services.trial import queue
from .services.lsm_engine import simulate
artifacts=Path(os.getenv('ARTIFACTS_DIR','/artifacts'))
heartbeat=artifacts/'worker.heartbeat'
artifacts.mkdir(parents=True,exist_ok=True)
LEASE=timedelta(seconds=120)
def claim(ident):
    """Atomically take a queued trial (or one whose worker lease expired) so two workers never both run it."""
    now=datetime.now(timezone.utc).replace(tzinfo=None)
    stale=now-LEASE
    with Session() as db:
        taken=db.execute(update(Trial).where(Trial.id==ident,Trial.result.is_(None),
            (Trial.status=='queued')|((Trial.status=='running')&((Trial.claimed_at==None)|(Trial.claimed_at<stale)))
        ).values(status='running',claimed_at=now)).rowcount
        db.commit();return taken==1
def run_one(ident):
    with Session() as db:
        x=db.get(Trial,ident)
        if not x:return
        if x.result is not None:
            # Result persisted before an interrupted status update; finish the transition only.
            if x.status not in ('passed','failed'):
                x.status='failed' if x.result.get('error') else 'passed';db.commit()
            return
    if not claim(ident):return
    with Session() as db:
        x=db.get(Trial,ident)
        if not x or x.result is not None:return
        try:
            result=simulate(x.input_snapshot['entries'],x.input_snapshot['config']);status='passed'
        except Exception as exc:result={'error':str(exc)[:500]};status='failed'
        x.result=result;x.status=status
        db.commit();(artifacts/f'lsm-trial-{ident}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
while True:
    try:
        heartbeat.write_text(str(time.time()));item=queue.blpop('lsm:jobs',timeout=2)
        if item:run_one(int(item[1]))
        else:
            with Session() as db:pending=list(db.scalars(select(Trial.id).where(Trial.status.in_(['queued','running']))))
            for ident in pending:run_one(ident)
    except Exception:traceback.print_exc();time.sleep(2)
