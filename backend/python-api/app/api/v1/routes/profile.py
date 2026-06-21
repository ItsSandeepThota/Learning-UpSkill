import time
import random
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.db.mongo import get_database
from app.schemas.profile import (
    ProfileResponse,
    BalanceUpdateRequest,
    AddCardRequest,
    ToggleCardFreezeRequest,
    UpdateCardLimitRequest,
    UpdateCardColorRequest,
    AddContactRequest
)

router = APIRouter()

RATES = {
    'GHS': 15.0,
    'USD': 1.0,
    'EUR': 0.92,
    'GBP': 0.79,
    'INR': 83.5
}

async def get_profile_response(email_clean: str, profile_dict: dict) -> ProfileResponse:
    db = get_database()
    user_doc = await db[settings.mongodb_collection].find_one({"email": email_clean})
    
    first_name = None
    last_name = None
    phone_no = None
    location = None
    account_no = None
    user_name = None

    if user_doc:
        first_name = user_doc.get("first_name") or user_doc.get("firstName")
        last_name = user_doc.get("last_name") or user_doc.get("lastName")
        phone_no = user_doc.get("phone_no") or user_doc.get("phoneNo") or user_doc.get("phone")
        location = user_doc.get("location")
        account_no = user_doc.get("account_no") or user_doc.get("accountNo")
        user_name = f"{first_name or ''} {last_name or ''}".strip()
        if not user_name:
            user_name = user_doc.get("user_name")

    if user_name and profile_dict.get("name") != user_name:
        profile_dict["name"] = user_name
        cards = profile_dict.get("cards") or []
        for card in cards:
            card["holder"] = user_name
        profile_dict["cards"] = cards
        await db["user_profiles"].update_one(
            {"email": email_clean},
            {"$set": {"name": user_name, "cards": cards}}
        )

    profile_dict["first_name"] = first_name
    profile_dict["last_name"] = last_name
    profile_dict["phone_no"] = phone_no
    profile_dict["location"] = location
    profile_dict["account_no"] = account_no

    return ProfileResponse(**profile_dict)

@router.get("/{email}", response_model=ProfileResponse)
async def get_or_create_profile(email: str) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    
    if profile is None:
        user_doc = await db[settings.mongodb_collection].find_one({"email": email_clean})
        user_name = None
        if user_doc:
            first_name = user_doc.get("first_name") or user_doc.get("firstName")
            last_name = user_doc.get("last_name") or user_doc.get("lastName")
            user_name = f"{first_name or ''} {last_name or ''}".strip()
            if not user_name:
                user_name = user_doc.get("user_name")
        
        if not user_name:
            user_name = email_clean.split('@')[0].capitalize()

        # Randomize balance and card details for each user to make it vary
        random_balance = round(random.uniform(1500.0, 12000.0), 2)
        card1_limit = float(random.choice([1500, 2000, 2500, 3000, 4000]))
        card2_limit = float(random.choice([500, 800, 1000, 1200, 1500]))
        card1_num = f"•••• •••• •••• {random.randint(1000, 9999)}"
        card2_num = f"•••• •••• •••• {random.randint(1000, 9999)}"

        profile = {
            "email": email_clean,
            "name": user_name,
            "balance": random_balance,
            "currency": "GHS",
            "cards": [
                {
                    "id": 1,
                    "number": card1_num,
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
                    "number": card2_num,
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
                    "id": time.time() - 3600,
                    "title": "Transfer outbound",
                    "subtitle": "To Contact Alpha",
                    "amount": -250.00,
                    "currency": "GHS",
                    "flag": "🇬🇭",
                    "time": "Today, 11:42 AM",
                    "status": "success"
                },
                {
                    "id": time.time() - 7200,
                    "title": "Salary credit",
                    "subtitle": "Employer deposit",
                    "amount": 3500.00,
                    "currency": "USD",
                    "flag": "🇺🇸",
                    "time": "Yesterday, 09:00 AM",
                    "status": "success"
                }
            ]
        }
        await db["user_profiles"].insert_one(profile)
    
    if not profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load profile")
    return await get_profile_response(email_clean, profile)

@router.post("/{email}/update-balance", response_model=ProfileResponse)
async def update_balance(email: str, payload: BalanceUpdateRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    rate = RATES.get(payload.currency.upper() if payload.currency else "", 1.0)
    usd_change = payload.amount / rate

    if payload.action == 'deduct':
        if usd_change > profile['balance']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds")
        new_balance = profile['balance'] - usd_change
    elif payload.action == 'add':
        new_balance = profile['balance'] + usd_change
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported action: '{payload.action}'. Only 'add' or 'deduct' are allowed."
        )

    new_tx = {
        "id": time.time(),
        "title": payload.tx_title,
        "subtitle": payload.tx_subtitle,
        "amount": -payload.amount if payload.action == 'deduct' else payload.amount,
        "currency": payload.currency.upper() if payload.currency else payload.currency,
        "flag": payload.tx_flag,
        "time": "Just now",
        "status": "success"
    }

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {
            "$set": {"balance": new_balance},
            "$push": {
                "transactions": {
                    "$each": [new_tx],
                    "$position": 0
                }
            }
        }
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)

@router.post("/{email}/add-card", response_model=ProfileResponse)
async def add_card(email: str, payload: AddCardRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    card_id = len(profile.get('cards', [])) + 1
    last_digits = random.randint(1000, 9999)
    number = f"•••• •••• •••• {last_digits}"

    new_card = {
        "id": card_id,
        "number": number,
        "holder": profile['name'],
        "expiry": "08/31",
        "cvv": "***",
        "color": payload.color,
        "frozen": False,
        "limit": 1500.0,
        "type": payload.type
    }

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {"$push": {"cards": new_card}}
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)

@router.post("/{email}/toggle-card-freeze", response_model=ProfileResponse)
async def toggle_card_freeze(email: str, payload: ToggleCardFreezeRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    cards = profile.get('cards', [])
    for c in cards:
        if c['id'] == payload.card_id:
            c['frozen'] = not c['frozen']
            break

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {"$set": {"cards": cards}}
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)

@router.post("/{email}/update-card-limit", response_model=ProfileResponse)
async def update_card_limit(email: str, payload: UpdateCardLimitRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    cards = profile.get('cards', [])
    for c in cards:
        if c['id'] == payload.card_id:
            c['limit'] = payload.limit
            break

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {"$set": {"cards": cards}}
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)

@router.post("/{email}/update-card-color", response_model=ProfileResponse)
async def update_card_color(email: str, payload: UpdateCardColorRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    cards = profile.get('cards', [])
    for c in cards:
        if c['id'] == payload.card_id:
            c['color'] = payload.color
            break

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {"$set": {"cards": cards}}
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)

@router.post("/{email}/add-contact", response_model=ProfileResponse)
async def add_contact(email: str, payload: AddContactRequest) -> ProfileResponse:
    email_clean = email.lower().strip()
    db = get_database()
    profile = await db["user_profiles"].find_one({"email": email_clean})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    initials = "".join([part[0] for part in payload.name.split() if part]).upper()[:2]
    
    flag_to_currency = {'🇬🇭': 'GHS', '🇺🇸': 'USD', '🇪🇺': 'EUR', '🇬🇧': 'GBP', '🇮🇳': 'INR'}
    currency = flag_to_currency.get(payload.flag, 'GHS')

    new_contact = {
        "name": payload.name,
        "initials": initials,
        "avatarUrl": None,
        "currency": currency,
        "flag": payload.flag
    }

    await db["user_profiles"].update_one(
        {"email": email_clean},
        {"$push": {"contacts": new_contact}}
    )

    updated_profile = await db["user_profiles"].find_one({"email": email_clean})
    if not updated_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load updated profile")
    return await get_profile_response(email_clean, updated_profile)
