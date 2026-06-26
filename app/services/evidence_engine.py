import re
from typing import List, Optional, Tuple, Dict, Any
from app.models.request import TransactionHistoryItem
from app.models.response import EvidenceVerdictEnum
from datetime import datetime

class ComplaintSignals:
    def __init__(self, complaint: str, user_type: Optional[str] = None):
        self.complaint = complaint
        self.complaint_lower = complaint.lower()
        self.user_type = user_type
        self.amounts = self._extract_amounts()
        self.amount = self.amounts[0] if self.amounts else None
        self.time_reference = self._extract_time()
        self.counterparty = self._extract_counterparty()
        self.has_duplicate_keywords = any(kw in self.complaint_lower for kw in ["twice", "double", "duplicate", "two times"])
        self.case_type_hint = self._detect_case_type_hint()
        self.expected_type = self._detect_expected_type()
        self.expected_status = self._detect_expected_status()

    def _extract_amounts(self) -> List[float]:
        bn_to_en = {
            '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
            '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
        }
        text = self.complaint
        for bn, en in bn_to_en.items():
            text = text.replace(bn, en)
        
        matches = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        amounts = []
        for m in matches:
            if m.startswith('0') and '.' not in m:
                continue
            val = float(m)
            if val >= 10:
                amounts.append(val)
        return amounts

    def _extract_time(self) -> Optional[str]:
        if "today" in self.complaint_lower or "আজ" in self.complaint_lower:
            return "today"
        if "yesterday" in self.complaint_lower:
            return "yesterday"
        return None

    def _extract_counterparty(self) -> Optional[str]:
        matches = re.findall(r'\b(?:\+88)?01\d{9}\b', self.complaint)
        if matches:
            return matches[0]
        return None

    def _detect_case_type_hint(self) -> str:
        text = self.complaint_lower
        if any(kw in text for kw in ["otp", "pin", "scam", "phishing", "called me", "password", "blocked if i don't"]):
            return "phishing_or_social_engineering"
        if any(kw in text for kw in ["twice", "double", "duplicate"]):
            return "duplicate_payment"
        if any(kw in text for kw in ["wrong number", "wrong person", "wrong recipient", "by mistake", "brother"]):
            return "wrong_transfer"
        if any(kw in text for kw in ["settlement", "not settled", "sales of"]):
            return "merchant_settlement_delay"
        if any(kw in text for kw in ["cash in", "agent", "ক্যাশ ইন", "এজেন্ট"]):
            return "agent_cash_in_issue"
        if any(kw in text for kw in ["failed", "didn't go through", "app showed failed"]):
            return "payment_failed"
        if any(kw in text for kw in ["refund", "money back", "changed my mind"]):
            return "refund_request"
        return "other"

    def _detect_expected_type(self) -> Optional[str]:
        if self.case_type_hint == "wrong_transfer":
            return "transfer"
        if self.case_type_hint in ["payment_failed", "refund_request", "duplicate_payment"]:
            return "payment"
        if self.case_type_hint == "agent_cash_in_issue":
            return "cash_in"
        if self.case_type_hint == "merchant_settlement_delay":
            return "settlement"
        return None

    def _detect_expected_status(self) -> Optional[str]:
        if self.case_type_hint == "payment_failed":
            return "failed"
        if self.case_type_hint == "agent_cash_in_issue":
            return "pending"
        if self.case_type_hint == "merchant_settlement_delay":
            return "pending"
        return None

def detect_duplicate_payment(transactions: List[TransactionHistoryItem]) -> Optional[str]:
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
    for i in range(len(sorted_txns) - 1):
        for j in range(i + 1, len(sorted_txns)):
            t1, t2 = sorted_txns[i], sorted_txns[j]
            time_diff = (t2.timestamp - t1.timestamp).total_seconds()
            if (t1.amount == t2.amount and 
                t1.counterparty == t2.counterparty and
                time_diff <= 120):
                return t2.transaction_id
    return None

def match_transaction(complaint_signals: ComplaintSignals, transaction_history: Optional[List[TransactionHistoryItem]]) -> Tuple[Optional[str], float]:
    if not transaction_history:
        return None, 0.0

    if complaint_signals.case_type_hint == "duplicate_payment" or complaint_signals.has_duplicate_keywords:
        dup_id = detect_duplicate_payment(transaction_history)
        if dup_id:
            return dup_id, 3.0

    scores = {}
    for txn in transaction_history:
        score = 0.0
        
        if complaint_signals.amounts:
            for amt in complaint_signals.amounts:
                if txn.amount == amt:
                    score += 3.0
                    break
                elif abs(txn.amount - amt) / amt < 0.1:
                    score += 2.0
                    break
        
        if complaint_signals.time_reference:
            score += 2.0
        
        if complaint_signals.expected_type:
            if txn.type.value == complaint_signals.expected_type:
                score += 2.0
        
        if complaint_signals.expected_status:
            if txn.status.value == complaint_signals.expected_status:
                score += 1.0
        
        if complaint_signals.counterparty:
            cp_norm = complaint_signals.counterparty.replace("+88", "")
            txn_cp_norm = txn.counterparty.replace("+88", "")
            if cp_norm == txn_cp_norm:
                score += 2.0
        
        scores[txn.transaction_id] = score
    
    if not scores:
        return None, 0.0
    
    best_id = max(scores, key=scores.get)
    best_score = scores[best_id]
    
    top_scorers = [tid for tid, s in scores.items() if s == best_score]
    if len(top_scorers) > 1 and best_score > 0:
        return None, 0.0
    
    if best_score < 2.0:
        return None, 0.0
    
    return best_id, best_score

def determine_verdict(complaint_signals: ComplaintSignals, matched_txn_id: Optional[str], all_transactions: Optional[List[TransactionHistoryItem]]) -> EvidenceVerdictEnum:
    if not matched_txn_id or not all_transactions:
        return EvidenceVerdictEnum.insufficient_data
    
    matched_txn = next((t for t in all_transactions if t.transaction_id == matched_txn_id), None)
    if not matched_txn:
        return EvidenceVerdictEnum.insufficient_data
    
    inconsistencies = []
    
    if complaint_signals.case_type_hint == "wrong_transfer":
        same_recipient_count = sum(1 for t in all_transactions if t.counterparty == matched_txn.counterparty)
        if same_recipient_count >= 3:
            inconsistencies.append("established_recipient_pattern")
    
    if complaint_signals.amount and matched_txn.amount != complaint_signals.amount:
        inconsistencies.append("amount_mismatch")
    
    if complaint_signals.case_type_hint == "duplicate_payment":
        duplicates = [t for t in all_transactions if t.amount == matched_txn.amount and t.counterparty == matched_txn.counterparty]
        if len(duplicates) < 2:
            inconsistencies.append("no_duplicate_found")
            
    if inconsistencies:
        return EvidenceVerdictEnum.inconsistent
        
    return EvidenceVerdictEnum.consistent
