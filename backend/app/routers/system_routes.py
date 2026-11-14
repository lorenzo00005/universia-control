from fastapi import APIRouter, Depends

from app.config import get_settings
from app.deps import get_current_user
from app.models import User
from app.schemas import SystemInfoOut

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SystemInfoOut)
def system_info(_: User = Depends(get_current_user)) -> SystemInfoOut:
    return SystemInfoOut(waha_dashboard_url=get_settings().waha_public_url.rstrip("/"))
