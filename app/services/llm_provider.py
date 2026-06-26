import os
import google.generativeai as genai
from typing import Optional, Dict, List, Any
import json
import logging
from app.models.response import EvidenceVerdictEnum, CaseTypeEnum

logger = logging.getLogger("uvicorn.error")

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_texts(
    complaint: str,
    matched_txn_id: Optional[str],
    verdict: EvidenceVerdictEnum,
    case_type: CaseTypeEnum,
    language: Optional[str] = "en",
    user_type: Optional[str] = "customer",
    transaction_history: Optional[List[Any]] = None
) -> Dict[str, str]:
    """Generate agent_summary, recommended_next_action, customer_reply using Gemini 3.1 Flash Lite."""
    
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set. Using template-based fallback.")
        return _fallback_templates(complaint, matched_txn_id, verdict, case_type, language)
    
    try:
        system_instruction = """You are a customer support AI analyzer for QueueStorm, a digital financial platform in Bangladesh.
Your task is to analyze ticket metadata, the customer complaint, and transaction evidence, then generate structured support outputs.

Output JSON Format:
Provide a JSON object containing exactly three string fields:
- "agent_summary": A 1-2 sentence factual, concise summary of the case for internal staff.
- "recommended_next_action": The precise next step for the support agent, focusing on investigation or verification. Do NOT promise refunds or account changes.
- "customer_reply": An empathetic, professional reply to the customer in the same language as the complaint.

Strict Safety Rules:
1. NEVER promise refunds, reversals, or automatic account unblocking in the "customer_reply" or "recommended_next_action". Instead, state that the case is being reviewed.
2. NEVER request sensitive credentials (such as PIN, OTP, password, card CVV, or full card number) from the customer.
3. If the user type is not "merchant", the "customer_reply" MUST include a standard security reminder (e.g., "Please do not share your PIN or OTP with anyone.").
4. Always match the language tone and language of the complaint (English, Bangla, or mixed/Banglish). If the complaint is in Bangla, reply in Bangla. If it is mixed/Banglish, use natural, professional language.

Tone Adaptation:
- Customer: Empathetic, supportive, reassuring, and clear.
- Merchant: Professional, concise, business-like, focusing on transaction details.
- Agent: Technical, objective, and action-oriented.
- Unknown / Default: Professional, standard customer support tone."""

        model = genai.GenerativeModel(
            model_name='gemini-3.1-flash-lite',
            system_instruction=system_instruction
        )
        
        # Format transaction history for prompt
        txn_summary = "No transaction history provided."
        if transaction_history:
            txn_lines = []
            for txn in transaction_history:
                status_str = txn.status.value if hasattr(txn.status, 'value') else str(txn.status)
                type_str = txn.type.value if hasattr(txn.type, 'value') else str(txn.type)
                is_matched = " (MATCHED TRANSACTION)" if txn.transaction_id == matched_txn_id else ""
                txn_lines.append(
                    f"- Txn ID: {txn.transaction_id}{is_matched}, Timestamp: {txn.timestamp}, "
                    f"Type: {type_str}, Amount: {txn.amount} BDT, Counterparty: {txn.counterparty}, Status: {status_str}"
                )
            txn_summary = "\n".join(txn_lines)

        prompt = f"""Analyze this ticket request and generate the JSON response.

Ticket Metadata:
- Case Type: {case_type.value if hasattr(case_type, 'value') else str(case_type)}
- Evidence Verdict: {verdict.value if hasattr(verdict, 'value') else str(verdict)}
- User Type (Tone): {user_type}
- Language: {language}

Sanitized Customer Complaint:
{complaint}

Transaction History:
{txn_summary}

Matched Transaction ID: {matched_txn_id or "None"}

Remember: Return ONLY valid JSON with fields: "agent_summary", "recommended_next_action", and "customer_reply"."""

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3,
                max_output_tokens=500
            ),
            request_options={"timeout": 15.0}
        )
        
        # Clean response text if wrapped in code block
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        result = json.loads(text)
        
        # Verify required fields exist
        if not all(k in result for k in ["agent_summary", "recommended_next_action", "customer_reply"]):
            raise ValueError("Missing required fields in LLM response JSON")
            
        return {
            "agent_summary": str(result["agent_summary"]),
            "recommended_next_action": str(result["recommended_next_action"]),
            "customer_reply": str(result["customer_reply"])
        }
        
    except Exception as e:
        logger.error(f"LLM error (falling back to templates): {e}", exc_info=True)
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
