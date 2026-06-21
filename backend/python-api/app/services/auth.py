import json
import uuid
from pathlib import Path

from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.mongo import get_database
from app.schemas.auth import AuthRecordCreate, AuthRecordResponse, now_utc


fallback_path = Path(__file__).resolve().parents[2] / "data" / "auth_records.jsonl"


async def record_auth_event(payload: AuthRecordCreate) -> AuthRecordResponse:
    database = get_database()
    document = payload.model_dump(by_alias=True)
    created_at = now_utc()
    document["created_on"] = created_at
    document["modified_on"] = created_at.isoformat()
    document["email"] = payload.email.lower()
    document["user_name"] = payload.email.split("@", 1)[0]
    document["account_no"] = f"SB{created_at.strftime('%Y%m%d%H%M%S')}"
    document["csv_no"] = 0
    document["record_type"] = payload.mode

    try:
        result = await database[settings.mongodb_collection].insert_one(document)
        inserted_id = str(result.inserted_id)
    except PyMongoError:
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        inserted_id = f"local-{uuid.uuid4().hex[:12]}"
        document["inserted_id"] = inserted_id
        with fallback_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(document, default=str) + "\n")

    return AuthRecordResponse(
        inserted_id=inserted_id,
        created_at=created_at,
        message="Shizen Bank record saved successfully",
    )