from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_admin
from app.models import PipelineStage, User
from app.schemas import StageCreate, StageOut

router = APIRouter(prefix="/stages", tags=["pipeline"])


@router.get("", response_model=list[StageOut])
def list_stages(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(PipelineStage).order_by(PipelineStage.position)).all()


@router.post("", response_model=StageOut, status_code=status.HTTP_201_CREATED)
def create_stage(data: StageCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    stage = PipelineStage(**data.model_dump())
    db.add(stage)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una etapa con ese nombre") from exc
    return stage
