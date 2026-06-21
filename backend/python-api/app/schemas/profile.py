from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class CardSchema(BaseModel):
    id: int
    number: str
    holder: str
    expiry: str
    cvv: str
    color: str
    frozen: bool
    limit: float
    type: str

class ContactSchema(BaseModel):
    name: str
    initials: str
    avatarUrl: Optional[str] = None
    currency: str
    flag: str

class TransactionSchema(BaseModel):
    id: float
    title: str
    subtitle: str
    amount: float
    currency: str
    flag: str
    time: str
    status: str

class ProfileResponse(BaseModel):
    email: str
    name: str
    balance: float
    currency: str
    cards: List[CardSchema] = []
    contacts: List[ContactSchema] = []
    transactions: List[TransactionSchema] = []
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_no: Optional[str] = None
    location: Optional[str] = None
    account_no: Optional[str] = None

class BalanceUpdateRequest(BaseModel):
    amount: float
    currency: str
    action: str  # 'add' | 'deduct'
    tx_title: str
    tx_subtitle: str
    tx_flag: str

class AddCardRequest(BaseModel):
    type: str  # 'debit' | 'credit'
    color: str

class ToggleCardFreezeRequest(BaseModel):
    card_id: int

class UpdateCardLimitRequest(BaseModel):
    card_id: int
    limit: float

class UpdateCardColorRequest(BaseModel):
    card_id: int
    color: str

class AddContactRequest(BaseModel):
    name: str
    flag: str
