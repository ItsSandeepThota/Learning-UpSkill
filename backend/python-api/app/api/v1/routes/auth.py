import traceback

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.schemas.auth import AuthRecordCreate, AuthRecordResponse, AuthVerifyRequest
from app.services.auth import record_auth_event, verify_registration_otp

router = APIRouter()


@router.post("/records", response_model=AuthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_auth_record(payload: AuthRecordCreate, background_tasks: BackgroundTasks) -> AuthRecordResponse:
    try:
        return await record_auth_event(payload, background_tasks)
    except HTTPException:
        raise
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unable to save auth record") from exc


@router.post("/verify", response_model=AuthRecordResponse, status_code=status.HTTP_200_OK)
async def verify_auth(payload: AuthVerifyRequest) -> AuthRecordResponse:
    try:
        return await verify_registration_otp(payload)
    except HTTPException:
        raise
    except Exception as exc:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unable to verify registration code") from exc