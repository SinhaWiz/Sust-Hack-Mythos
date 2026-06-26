# Sust-Hack-Mythos

**QueueStorm Investigator** - AI-powered customer support investigation API for digital finance platforms.

## Features

✅ **Evidence-Based Investigation**: Cross-references complaints against transaction history  
✅ **Multi-Language Support**: English, Bangla, and mixed language complaints  
✅ **Safety Guardrails**: Blocks credential requests, unauthorized promises, and phishing patterns  
✅ **Smart Classification**: Automatic case type, severity, and department routing  
✅ **LLM Integration**: Uses Google Gemini 2.5 Flash with fallback templates  
✅ **10 Test Cases**: Validates wrong transfers, duplicates, phishing, and more

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variable (Optional)
```bash
# Copy example
cp .env.example .env

# Edit .env and add your Gemini API key (optional - uses fallback templates if not provided)
GEMINI_API_KEY=your_key_here
```

### 3. Run Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Test
```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_phase1.py -v  # Schema validation
pytest tests/test_phase2.py -v  # Sample cases
pytest tests/test_integration.py -v  # End-to-end
```

## API Endpoints

### `GET /health`
Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

### `POST /analyze-ticket`
Analyze a customer complaint ticket.

**Request:**
```json
{
  "ticket_id": "TKT-001",
  "complaint": "I sent 5000 taka to wrong number",
  "language": "en",
  "user_type": "customer",
  "transaction_history": [
    {
      "transaction_id": "TXN-9101",
      "timestamp": "2026-06-26T14:08:22Z",
      "type": "transfer",
      "amount": 5000.0,
      "counterparty": "+8801712345678",
      "status": "completed"
    }
  ]
}
```

**Response:**
```json
{
  "ticket_id": "TKT-001",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports wrong transfer...",
  "recommended_next_action": "Verify transaction details...",
  "customer_reply": "We have noted your concern. Please do not share your PIN or OTP with anyone.",
  "human_review_required": true,
  "confidence": 5.0
}
```

## Architecture

```
Request → Evidence Engine → Classifier → LLM Generator → Safety Guardrails → Response
```

### Components
- **Evidence Engine**: Matches transactions, determines verdict
- **Classifier**: Case type, severity, department routing
- **LLM Provider**: Text generation with Gemini (fallback templates)
- **Safety Guardrails**: Post-processing filters for safety compliance

## Test Coverage

✅ **Phase 1**: Schema validation, error handling  
✅ **Phase 2**: 10 sample cases covering all scenarios  
✅ **Integration**: End-to-end flows with safety checks

### Test Cases
1. Wrong transfer (consistent evidence)
2. Payment failed
3. Refund request
4. Duplicate payment
5. Merchant settlement delay
6. Agent cash-in issue (Bangla)
7. Phishing/social engineering
8. Inconsistent evidence (established recipient)
9. Insufficient data (vague complaint)
10. Insufficient data (Bangla, no history)

## Safety Guarantees

🔒 **Never asks for**: PIN, OTP, password, card numbers  
🔒 **Never promises**: Refunds, reversals, account restoration  
🔒 **Always includes**: PIN/OTP safety reminder for customers  
🔒 **Blocks**: Third-party contact redirects  

## Performance

- **Response Time**: < 5 seconds (with LLM), < 1 second (fallback)
- **Timeout**: 30 seconds enforced
- **Memory**: ~100MB baseline
- **CPU**: 2 vCPU recommended

## Development

```bash
# Run server with auto-reload
uvicorn app.main:app --reload

# Run tests with coverage
pytest tests/ --cov=app --cov-report=html
```

## Project Structure

```
.
├── app/
│   ├── main.py                    # FastAPI app & routes
│   ├── models/
│   │   ├── request.py             # Request schemas
│   │   └── response.py            # Response schemas
│   └── services/
│       ├── evidence_engine.py     # Transaction matching & verdict
│       ├── classifier.py          # Case classification logic
│       ├── llm_provider.py        # Gemini integration
│       └── safety_guardrails.py   # Safety post-processing
├── tests/
│   ├── test_phase1.py             # Schema validation tests
│   ├── test_phase2.py             # Sample case tests
│   └── test_integration.py        # End-to-end tests
├── start_doc/
│   └── SUST_Preli_Sample_Cases.json  # Test data
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT License - SUST CSE Carnival 2026 Hackathon