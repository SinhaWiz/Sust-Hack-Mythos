from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum
from datetime import datetime

class LanguageEnum(str, Enum):
    en = "en"
    bn = "bn"
    mixed = "mixed"

class ChannelEnum(str, Enum):
    in_app_chat = "in_app_chat"
    call_center = "call_center"
    email = "email"
    merchant_portal = "merchant_portal"
    field_agent = "field_agent"

class UserTypeEnum(str, Enum):
    customer = "customer"
    merchant = "merchant"
    agent = "agent"
    unknown = "unknown"

class TransactionTypeEnum(str, Enum):
    transfer = "transfer"
    payment = "payment"
    cash_in = "cash_in"
    cash_out = "cash_out"
    settlement = "settlement"
    refund = "refund"

class TransactionStatusEnum(str, Enum):
    completed = "completed"
    failed = "failed"
    pending = "pending"
    reversed = "reversed"

class TransactionHistoryItem(BaseModel):
    transaction_id: str
    timestamp: datetime
    type: TransactionTypeEnum
    amount: float
    counterparty: str
    status: TransactionStatusEnum

class AnalyzeTicketRequest(BaseModel):
    ticket_id: str
    complaint: str = Field(..., min_length=1, description="Complaint text cannot be empty")
    language: Optional[LanguageEnum] = None
    channel: Optional[ChannelEnum] = None
    user_type: Optional[UserTypeEnum] = None
    campaign_context: Optional[str] = None
    transaction_history: Optional[List[TransactionHistoryItem]] = None
    metadata: Optional[Dict[str, Any]] = None
