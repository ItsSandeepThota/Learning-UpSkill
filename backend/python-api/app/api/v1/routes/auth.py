import traceback

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import AuthRecordCreate, AuthRecordResponse
from app.services.auth import record_auth_event

router = APIRouter()


@router.post("/records", response_model=AuthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_auth_record(payload: AuthRecordCreate) -> AuthRecordResponse:
    try:
        return await record_auth_event(payload)
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unable to save auth record") from exc