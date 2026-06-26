from typing import Optional
from app.models.request import UserTypeEnum
from app.models.response import CaseTypeEnum, SeverityEnum, DepartmentEnum, EvidenceVerdictEnum
from app.services.evidence_engine import ComplaintSignals

def classify_case_type(complaint_signals: ComplaintSignals, verdict: EvidenceVerdictEnum) -> CaseTypeEnum:
    hint = complaint_signals.case_type_hint
    try:
        return CaseTypeEnum(hint)
    except ValueError:
        return CaseTypeEnum.other

def determine_severity(case_type: CaseTypeEnum, verdict: EvidenceVerdictEnum, complaint_signals: ComplaintSignals) -> SeverityEnum:
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return SeverityEnum.critical
    
    if case_type == CaseTypeEnum.wrong_transfer and verdict == EvidenceVerdictEnum.insufficient_data:
        return SeverityEnum.medium

    if case_type in [CaseTypeEnum.wrong_transfer, CaseTypeEnum.payment_failed, CaseTypeEnum.duplicate_payment, CaseTypeEnum.agent_cash_in_issue]:
        if verdict == EvidenceVerdictEnum.inconsistent:
            return SeverityEnum.medium
        return SeverityEnum.high
        
    if case_type == CaseTypeEnum.merchant_settlement_delay:
        return SeverityEnum.medium
        
    return SeverityEnum.low

def determine_department(case_type: CaseTypeEnum, user_type: Optional[UserTypeEnum]) -> DepartmentEnum:
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return DepartmentEnum.fraud_risk
    if case_type == CaseTypeEnum.wrong_transfer:
        return DepartmentEnum.dispute_resolution
    if case_type in [CaseTypeEnum.payment_failed, CaseTypeEnum.duplicate_payment]:
        return DepartmentEnum.payments_ops
    if case_type == CaseTypeEnum.merchant_settlement_delay or user_type == UserTypeEnum.merchant:
        return DepartmentEnum.merchant_operations
    if case_type == CaseTypeEnum.agent_cash_in_issue:
        return DepartmentEnum.agent_operations
    return DepartmentEnum.customer_support

def determine_human_review_required(case_type: CaseTypeEnum, verdict: EvidenceVerdictEnum, severity: SeverityEnum) -> bool:
    if case_type == CaseTypeEnum.phishing_or_social_engineering:
        return True
    if verdict == EvidenceVerdictEnum.inconsistent:
        return True
    if case_type == CaseTypeEnum.wrong_transfer and verdict == EvidenceVerdictEnum.insufficient_data:
        return False
    if case_type == CaseTypeEnum.wrong_transfer:
        return True
    if case_type == CaseTypeEnum.duplicate_payment:
        return True
    if case_type == CaseTypeEnum.agent_cash_in_issue:
        return True
    if case_type == CaseTypeEnum.payment_failed:
        return False
    if case_type == CaseTypeEnum.merchant_settlement_delay:
        return False
    return False
