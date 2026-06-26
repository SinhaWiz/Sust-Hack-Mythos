import os
import google.generativeai as genai
from typing import Optional, Dict
import json
from app.models.response import EvidenceVerdictEnum, CaseTypeEnum

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_texts(
    complaint: str,
    matched_txn_id: Optional[str],
    verdict: EvidenceVerdictEnum,
    case_type: CaseTypeEnum,
    language: Optional[str] = "en"
) -> Dict[str, str]:
    """Generate agent_summary, recommended_next_action, customer_reply using LLM."""
    
    if not GEMINI_API_KEY:
        return _fallback_templates(complaint, matched_txn_id, verdict, case_type, language)
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""You are a customer support AI for a digital finance platform. Generate professional responses.

COMPLAINT: {complaint}
MATCHED_TRANSACTION: {matched_txn_id or "None"}
EVIDENCE_VERDICT: {verdict.value}
CASE_TYPE: {case_type.value}
LANGUAGE: {language or "en"}

Generate JSON with exactly these fields:
1. agent_summary: 1-2 sentence factual summary for internal agent
2. recommended_next_action: Specific operational action (no promises of refunds)
3. customer_reply: Professional response in the same language as complaint. MUST include PIN/OTP safety reminder. NO promises of refunds. NO credential requests.

Rules:
- Never promise refunds or reversals
- Never ask for PIN, OTP, password
- Always remind about PIN/OTP safety
- Be professional and helpful
- Match language of complaint

Return ONLY valid JSON."""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
                max_output_tokens=500
            )
        )
        
        result = json.loads(response.text)
        return {
            "agent_summary": result.get("agent_summary", ""),
            "recommended_next_action": result.get("recommended_next_action", ""),
            "customer_reply": result.get("customer_reply", "")
        }
        
    except Exception as e:
        print(f"LLM error: {e}")
        return _fallback_templates(complaint, matched_txn_id, verdict, case_type, language)

def _fallback_templates(complaint: str, matched_txn_id: Optional[str], verdict: EvidenceVerdictEnum, case_type: CaseTypeEnum, language: Optional[str]) -> Dict[str, str]:
    """Template-based fallback when LLM fails."""
    
    templates = {
        "wrong_transfer": {
            "en": {
                "summary": f"Customer reports wrong transfer. Transaction {matched_txn_id or 'not identified'}. Evidence: {verdict.value}.",
                "action": "Verify transaction details and contact recipient if possible.",
                "reply": f"We have noted your concern about transaction {matched_txn_id or 'mentioned'}. Our dispute team will review the case. Please do not share your PIN or OTP with anyone."
            },
            "bn": {
                "summary": f"গ্রাহক ভুল ট্রান্সফার রিপোর্ট করেছেন। ট্রান্সাকশন {matched_txn_id or 'চিহ্নিত নয়'}। প্রমাণ: {verdict.value}।",
                "action": "ট্রান্সাকশনের বিস্তারিত যাচাই করুন এবং প্রাপকের সাথে যোগাযোগ করুন।",
                "reply": f"আমরা আপনার সমস্যা নোট করেছি। আমাদের টিম পর্যালোচনা করবে। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
            }
        },
        "payment_failed": {
            "en": {
                "summary": f"Payment failed but may have impacted balance. Transaction {matched_txn_id or 'not identified'}.",
                "action": "Check transaction status and initiate reversal if applicable.",
                "reply": "We are reviewing the transaction. Any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone."
            }
        },
        "refund_request": {
            "en": {
                "summary": "Customer requesting refund.",
                "action": "Review refund policy and merchant terms.",
                "reply": "Refunds depend on the applicable policy. We will review your request. Please do not share your PIN or OTP with anyone."
            }
        },
        "duplicate_payment": {
            "en": {
                "summary": f"Possible duplicate payment. Transaction {matched_txn_id or 'not identified'}.",
                "action": "Verify duplicate charges and process reversal if confirmed.",
                "reply": "We are investigating the duplicate payment. Please do not share your PIN or OTP with anyone."
            }
        },
        "phishing_or_social_engineering": {
            "en": {
                "summary": "Security alert: Possible phishing or social engineering attempt.",
                "action": "URGENT: Flag account for security review. Contact customer immediately.",
                "reply": "WARNING: Never share your PIN, OTP, or password with anyone. We will never ask for these. If you shared credentials, contact us immediately."
            }
        }
    }
    
    lang = "bn" if language == "bn" else "en"
    case_templates = templates.get(case_type.value, templates["refund_request"])
    lang_template = case_templates.get(lang, case_templates.get("en", case_templates["en"]))
    
    return {
        "agent_summary": lang_template["summary"],
        "recommended_next_action": lang_template["action"],
        "customer_reply": lang_template["reply"]
    }
