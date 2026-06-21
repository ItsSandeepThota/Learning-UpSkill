import hashlib
import json
import os
import random
import re
import smtplib
import uuid
from email.mime.text import MIMEText
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status
from pymongo.errors import PyMongoError

from app.core.config import settings
from app.db.mongo import get_database
from app.schemas.auth import AuthRecordCreate, AuthRecordResponse, AuthVerifyRequest, now_utc


fallback_path = Path(__file__).resolve().parents[2] / "data" / "auth_records.jsonl"

PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{10,}$"
)
NAME_REGEX = re.compile(r"^[a-zA-Z\s\-]+$")


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return key.hex(), salt.hex()


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    try:
        salt_bytes = bytes.fromhex(salt)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt_bytes,
            100000
        )
        return key.hex() == hashed_password
    except Exception:
        return False


def send_verification_email(to_email: str, code: str) -> bool:
    if not settings.smtp_host:
        # Dev fallback: no SMTP server configured, log code to console
        print(f"\n[OTP DEVELOPMENT FALLBACK] Verification code for {to_email}: {code}\n")
        return False

    subject = "Shizen Bank - Registration Verification Code"
    body = f"""Hello,

Your verification code for registering your Shizen Bank profile is: {code}

This code is valid for 10 minutes. If you did not request this, please ignore this email.

Best regards,
Shizen Bank Security Team
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_username or "no-reply@shizenbank.com"
    msg["To"] = to_email

    try:
        if settings.smtp_port == 465:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)
            server.starttls()

        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)

        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending SMTP email: {e}")
        # Always print OTP as fallback in console
        print(f"\n[OTP SMTP FAILURE FALLBACK] Verification code for {to_email}: {code}\n")
        return False


async def record_auth_event(payload: AuthRecordCreate) -> AuthRecordResponse:
    database = get_database()
    email_clean = payload.email.lower().strip()
    inserted_id = ""

    # Look for the user in the "users" collection (which settings.mongodb_collection points to)
    user_doc = await database[settings.mongodb_collection].find_one({"email": email_clean})

    if payload.mode == "register":
        # 1. Enforce Gmail domain requirement
        if not email_clean.endswith("@gmail.com"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Gmail addresses (@gmail.com) are allowed to register."
            )

        # 2. Real-time deliverability check
        try:
            validate_email(email_clean, check_deliverability=True)
        except EmailNotValidError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Please enter a genuine Gmail address. Reason: {exc}"
            )

        # 3. Enforce first_name and last_name character constraints
        if not payload.first_name or not payload.first_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name is required for registration."
            )
        if not payload.last_name or not payload.last_name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last name is required for registration."
            )

        if not NAME_REGEX.match(payload.first_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name can only contain letters, spaces, and hyphens."
            )
        if not NAME_REGEX.match(payload.last_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last name can only contain letters, spaces, and hyphens."
            )

        # 4. Enforce password complexity
        if not PASSWORD_REGEX.match(payload.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 10 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
            )

        if user_doc is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email already exists."
            )

        # Clean up any existing pending registration for this email
        await database["pending_registrations"].delete_many({"email": email_clean})

        # Generate a random 6-digit OTP code
        otp_code = f"{random.randint(100000, 999999)}"

        # Prepare document for pending registry
        pending_document = {
            "email": email_clean,
            "password": payload.password,
            "firstName": payload.first_name,
            "lastName": payload.last_name,
            "code": otp_code,
            "created_at": now_utc()
        }

        try:
            await database["pending_registrations"].insert_one(pending_document)
        except PyMongoError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate registration verification."
            ) from exc

        # Send SMTP verification email
        send_verification_email(email_clean, otp_code)

        return AuthRecordResponse(
            inserted_id="pending",
            created_at=now_utc(),
            message="Verification code sent to your Gmail. Please check your inbox.",
        )

    elif payload.mode == "login":
        if user_doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found. Please register first."
            )

        stored_hash = user_doc.get("password_hash")
        stored_salt = user_doc.get("password_salt")

        if stored_hash is not None and stored_salt is not None:
            if not verify_password(payload.password, stored_hash, stored_salt):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password."
                )
            inserted_id = str(user_doc.get("_id", ""))
        else:
            password_hash, password_salt = hash_password(payload.password)
            await database[settings.mongodb_collection].update_one(
                {"email": email_clean},
                {"$set": {"password_hash": password_hash, "password_salt": password_salt}}
            )
            inserted_id = str(user_doc.get("_id", ""))

    # Log the auth event in "auth_events" collection
    created_at = now_utc()
    event_doc = {
        "email": email_clean,
        "record_type": payload.mode,
        "created_on": created_at,
        "source": payload.source
    }

    try:
        await database["auth_events"].insert_one(event_doc)
    except PyMongoError:
        pass

    return AuthRecordResponse(
        inserted_id=inserted_id,
        created_at=created_at,
        message="Shizen Bank record saved successfully",
    )


async def verify_registration_otp(payload: AuthVerifyRequest) -> AuthRecordResponse:
    database = get_database()
    email_clean = payload.email.lower().strip()

    # Query pending registrations
    pending_record = await database["pending_registrations"].find_one({
        "email": email_clean,
        "code": payload.code
    })

    if not pending_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code."
        )

    # Check if user already exists (edge case)
    existing_user = await database[settings.mongodb_collection].find_one({"email": email_clean})
    if existing_user:
        await database["pending_registrations"].delete_many({"email": email_clean})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Complete registration: hash password and insert into users
    password_hash, password_salt = hash_password(pending_record["password"])
    created_at = now_utc()
    user_document = {
        "email": email_clean,
        "password_hash": password_hash,
        "password_salt": password_salt,
        "firstName": pending_record["firstName"],
        "lastName": pending_record["lastName"],
        "user_name": f"{pending_record['firstName']} {pending_record['lastName']}".strip() or email_clean.split("@", 1)[0],
        "account_no": f"SB{created_at.strftime('%Y%m%d%H%M%S')}",
        "csv_no": 0,
        "created_on": created_at,
        "modified_on": created_at.isoformat()
    }

    try:
        # 1. Insert user
        user_result = await database[settings.mongodb_collection].insert_one(user_document)
        inserted_id = str(user_result.inserted_id)

        # 2. Initialize default user profile
        random_balance = round(random.uniform(1500.0, 12000.0), 2)
        card1_limit = float(random.choice([1500, 2000, 2500, 3000, 4000]))
        card2_limit = float(random.choice([500, 800, 1000, 1200, 1500]))
        user_name = user_document["user_name"]

        profile_doc = {
            "email": email_clean,
            "name": user_name,
            "balance": random_balance,
            "currency": "GHS",
            "cards": [
                {
                    "id": 1,
                    "number": f"•••• •••• •••• {random.randint(1000, 9999)}",
                    "holder": user_name,
                    "expiry": "12/30",
                    "cvv": "***",
                    "color": "blue",
                    "frozen": False,
                    "limit": card1_limit,
                    "type": "debit"
                },
                {
                    "id": 2,
                    "number": f"•••• •••• •••• {random.randint(1000, 9999)}",
                    "holder": user_name,
                    "expiry": "06/28",
                    "cvv": "***",
                    "color": "purple",
                    "frozen": False,
                    "limit": card2_limit,
                    "type": "credit"
                }
            ],
            "contacts": [
                {
                    "name": "Contact Alpha",
                    "initials": "CA",
                    "avatarUrl": "assets/grace_avatar.png",
                    "currency": "GHS",
                    "flag": "🇬🇭"
                },
                {
                    "name": "Contact Beta",
                    "initials": "CB",
                    "avatarUrl": None,
                    "currency": "GHS",
                    "flag": "🇬🇭"
                }
            ],
            "transactions": [
                {
                    "id": now_utc().timestamp() - 3600,
                    "title": "Transfer outbound",
                    "subtitle": "To Contact Alpha",
                    "amount": -250.00,
                    "currency": "GHS",
                    "flag": "🇬🇭",
                    "time": "Today, 11:42 AM",
                    "status": "success"
                }
            ]
        }
        await database["user_profiles"].insert_one(profile_doc)

        # 3. Log the registration event in auth_events
        event_doc = {
            "email": email_clean,
            "record_type": "register",
            "created_on": created_at,
            "source": "web-auth-page"
        }
        await database["auth_events"].insert_one(event_doc)

        # 4. Clean up pending record
        await database["pending_registrations"].delete_many({"email": email_clean})

    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete registration database entries."
        ) from exc

    return AuthRecordResponse(
        inserted_id=inserted_id,
        created_at=created_at,
        message="Registration verified and completed successfully."
    )