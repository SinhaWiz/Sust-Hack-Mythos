import re

with open("/Users/nayburrahman/Documents/Sust-Hack-Mythos-1/HLD.md", "r") as f:
    content = f.read()

# 1. System Overview text
content = content.replace("""┌──────────────────────────────────────────────────────────────────────┐
│                    QueueStorm Investigator Service                    │
│                                                                      │
│  ┌─────────┐   ┌──────────────┐   ┌────────────┐   ┌─────────────┐ │
│  │  HTTP    │──▶│   Request    │──▶│  Evidence   │──▶│  Response   │ │
│  │  Layer   │   │  Validator   │   │  Reasoning  │   │  Builder    │ │
│  │(FastAPI) │   │  & Parser    │   │  Engine     │   │  & Safety   │ │
│  └─────────┘   └──────────────┘   └────────────┘   └─────────────┘ │
│       │                                  │                 │         │
│       │                                  ▼                 ▼         │
│       │                           ┌────────────┐   ┌─────────────┐  │
│       │                           │    LLM     │   │   Safety    │  │
│       │                           │  Provider  │   │  Guardrails │  │
│       │                           │ (Gemini)   │   │   Module    │  │
│       │                           └────────────┘   └─────────────┘  │
│       │                                                              │
│  ┌─────────┐                                                         │
│  │ /health │  → {"status": "ok"}                                     │
│  └─────────┘                                                         │
└──────────────────────────────────────────────────────────────────────┘""", """┌──────────────────────────────────────────────────────────────────────────────────┐
│                          QueueStorm Investigator Enterprise System                 │
│                                                                                  │
│   ┌────────┐     ┌─────────┐    ┌──────────┐     ┌──────────────┐                │
│   │ NGINX  │────▶│ FastAPI │───▶│ RabbitMQ │────▶│ Worker Nodes │                │
│   │ Proxy  │     │ Gateway │    │  (RPC)   │     │ (Core Logic) │                │
│   └────────┘     └─────────┘    └──────────┘     └──────────────┘                │
│                       │                                 │                        │
│                       ▼                                 │                        │
│                  ┌────────┐                             ▼                        │
│                  │ Redis  │◀────────────────────────────┘                        │
│                  │(Cache) │                                                      │
│                  └────────┘                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘""")

content = content.replace("""| **HTTP Layer** | Route handling, CORS, content-type validation |
| **Request Validator** | JSON schema validation, required field checks, enum validation |
| **Evidence Reasoning Engine** | Transaction matching, evidence verdict, case classification, severity, department routing |
| **LLM Provider** | Natural language understanding, text generation (summaries, replies) |
| **Safety Guardrails** | Post-processing filter on all text outputs — blocks credential requests, unauthorized promises, third-party redirects, prompt injection |
| **Response Builder** | Assembles the final JSON response with all required fields |""", """| **NGINX Proxy** | Reverse proxy, rate limiting, connection management |
| **FastAPI Gateway** | Route handling, JSON schema validation, RPC queue publisher |
| **Redis** | Caching identical requests to save LLM calls, tracking rate limits |
| **RabbitMQ** | Message broker for RPC requests, distributes load among workers |
| **Worker Node (Evidence Reasoning)** | Transaction matching, evidence verdict, case classification, severity, department routing |
| **Worker Node (LLM Provider)** | Natural language understanding, text generation (summaries, replies) |
| **Worker Node (Safety Guardrails)** | Post-processing filter on all text outputs — blocks credential requests, unauthorized promises, third-party redirects |
| **Worker Node (Response Builder)** | Assembles the final JSON response with all required fields, publishes back to RabbitMQ |""")


# 2. Architecture Diagram (Mermaid)
mermaid_old = """flowchart TD
    subgraph Client["Judge Harness / Client"]
        A["POST /analyze-ticket"] --> B["HTTP Request"]
        H["GET /health"] --> I["Health Check"]
    end

    subgraph Service["QueueStorm Investigator"]
        B --> C["Request Validator"]
        C -->|"Invalid"| D["400/422 Error Response"]
        C -->|"Valid"| E["Evidence Reasoning Engine"]
        
        E --> E1["Transaction Matcher"]
        E --> E2["Evidence Verdict Logic"]
        E --> E3["Case Classifier"]
        E --> E4["Severity Assessor"]
        E --> E5["Department Router"]
        
        E1 & E2 & E3 & E4 & E5 --> F["LLM Text Generator"]
        F --> F1["Agent Summary"]
        F --> F2["Recommended Next Action"]
        F --> F3["Customer Reply"]
        
        F1 & F2 & F3 --> G["Safety Guardrails"]
        G --> G1["Credential Check"]
        G --> G2["Refund Promise Check"]
        G --> G3["Third-Party Check"]
        G --> G4["Prompt Injection Defense"]
        
        G1 & G2 & G3 & G4 --> J["Response Builder"]
        J --> K["200 JSON Response"]
        
        I --> L["{'status': 'ok'}"]
    end

    subgraph External["External Services"]
        F -.->|"API Call"| M["Google Gemini API"]
    end"""

mermaid_new = """flowchart TD
    subgraph Client["Judge Harness / Client"]
        A["POST /analyze-ticket"] --> B["HTTP Request"]
        H["GET /health"] --> I["Health Check"]
    end

    subgraph Gateway["API Gateway Layer"]
        B --> N["NGINX Proxy"]
        N --> C["FastAPI Server"]
        I --> N
        N --> L["{'status': 'ok'}"]
        
        C --> C1["Request Validator"]
        C1 -->|"Invalid"| D["400/422 Error Response"]
        
        C1 -->|"Valid"| R1{"Redis Cache"}
        R1 -->|"Hit"| K["200 JSON Response (Cached)"]
        R1 -->|"Miss"| RMQ1["RabbitMQ (RPC Queue)"]
    end

    subgraph Workers["Worker Nodes"]
        RMQ1 --> E["Evidence Reasoning Engine"]
        
        E --> E1["Transaction Matcher"]
        E --> E2["Evidence Verdict Logic"]
        E --> E3["Case Classifier"]
        E --> E4["Severity Assessor"]
        E --> E5["Department Router"]
        
        E1 & E2 & E3 & E4 & E5 --> F["LLM Text Generator"]
        F --> F1["Agent Summary"]
        F --> F2["Recommended Next Action"]
        F --> F3["Customer Reply"]
        
        F1 & F2 & F3 --> G["Safety Guardrails"]
        G --> G1["Credential Check"]
        G --> G2["Refund Promise Check"]
        G --> G3["Third-Party Check"]
        G --> G4["Prompt Injection Defense"]
        
        G1 & G2 & G3 & G4 --> J["Response Builder"]
        J --> R2["Redis (Save Cache)"]
        J --> RMQ2["RabbitMQ (Callback Queue)"]
    end

    RMQ2 --> K["200 JSON Response"]

    subgraph External["External Services"]
        F -.->|"API Call"| M["Google Gemini API"]
    end"""
content = content.replace(mermaid_old, mermaid_new)

# 3. Complete Tech Stack
tech_old = """| Layer | Technology | Purpose |
|---|---|---|
| **Runtime** | Python 3.12 | Core language |
| **Framework** | FastAPI 0.115+ | HTTP endpoints, auto-validation |
| **Validation** | Pydantic v2 | Request/response schema enforcement |
| **LLM** | Google Gemini 2.0 Flash | NLU + text generation |
| **LLM SDK** | `google-generativeai` | API client |
| **Server** | Uvicorn | ASGI server |
| **Containerization** | Docker (python:3.12-slim) | Deployment |
| **Deployment** | Render / Railway / EC2 | Live URL |
| **Testing** | pytest + httpx | Integration tests |"""

tech_new = """| Layer | Technology | Purpose |
|---|---|---|
| **Reverse Proxy** | NGINX | Load balancing, rate limiting |
| **Cache & State** | Redis | Caching LLM responses, rate limiting |
| **Message Broker**| RabbitMQ | RPC queuing for high concurrency |
| **Runtime** | Python 3.12 | Core language |
| **Framework** | FastAPI 0.115+ | HTTP endpoints, auto-validation |
| **Validation** | Pydantic v2 | Request/response schema enforcement |
| **LLM** | Google Gemini 2.0 Flash | NLU + text generation |
| **Server** | Uvicorn | ASGI server |
| **Containerization** | Docker + Compose | Multi-container deployment |
| **Testing** | pytest + httpx | Integration tests |"""
content = content.replace(tech_old, tech_new)

# 4. Core Processing Pipeline - Start
pipe_old1 = """Step 1: VALIDATE REQUEST
    ├── Parse JSON body
    ├── Check required fields (ticket_id, complaint)
    ├── Validate enum values if present
    └── Return 400/422 on failure

Step 2: EXTRACT COMPLAINT SIGNALS (Rule-Based)"""
pipe_new1 = """Step 0: GATEWAY & CACHE
    ├── NGINX proxies request to FastAPI
    ├── FastAPI checks Redis for cached response by ticket_id hash
    │   └── If cache hit → Return 200 immediately
    └── If cache miss → Publish request to RabbitMQ RPC queue & await callback

Step 1: VALIDATE REQUEST (Worker or Gateway)
    ├── Parse JSON body
    ├── Check required fields (ticket_id, complaint)
    ├── Validate enum values if present
    └── Return 400/422 on failure

Step 2: EXTRACT COMPLAINT SIGNALS (Rule-Based)"""
content = content.replace(pipe_old1, pipe_new1)


# 5. Core Processing Pipeline - End
pipe_old2 = """Step 8: BUILD RESPONSE
    ├── Assemble all fields into response JSON
    ├── Add optional fields (confidence, reason_codes)
    ├── Validate against output schema (Pydantic)
    └── Return 200 with response body"""
pipe_new2 = """Step 8: BUILD RESPONSE & CACHE
    ├── Assemble all fields into response JSON
    ├── Add optional fields (confidence, reason_codes)
    ├── Validate against output schema (Pydantic)
    ├── Save JSON response to Redis Cache (TTL: 24 hours)
    ├── Publish response to RabbitMQ callback queue
    └── FastAPI Gateway consumes callback and returns HTTP 200"""
content = content.replace(pipe_old2, pipe_new2)

# 6. Deployment Strategy
deploy_old = """### Fallback: Docker Image (Path B)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build & Run
docker build -t queuestorm-mythos .
docker run -p 8000:8000 --env-file .env queuestorm-mythos
```"""
deploy_new = """### Primary: Docker Compose Enterprise Stack

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api
      
  redis:
    image: redis:alpine
    expose:
      - 6379

  rabbitmq:
    image: rabbitmq:3-management-alpine
    expose:
      - 5672
      - 15672

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    expose:
      - 8000
    env_file: .env
    depends_on:
      - redis
      - rabbitmq

  worker:
    build: .
    command: python -m app.worker
    env_file: .env
    depends_on:
      - redis
      - rabbitmq
    deploy:
      replicas: 3
```

```bash
# Build & Run Stack
docker-compose up -d --build
```"""
content = content.replace(deploy_old, deploy_new)

# 7. Project Structure
struct_old = """├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, route definitions"""
struct_new = """├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, route definitions, RPC client
│   ├── worker.py                  # RabbitMQ consumer, core logic runner
│   ├── broker.py                  # RabbitMQ connection and queues
│   ├── cache.py                   # Redis connection and logic"""
content = content.replace(struct_old, struct_new)


# 8. Checklist Phase 6
chk_old = """### Phase 6: Deployment & Submission Requirements (Priority 4)

- [ ] Create `Dockerfile` (python:3.12-slim based)
- [ ] Create `.env.example` with all required variable names
- [ ] Test Docker build locally
- [ ] Test Docker run locally with `--env-file`
- [ ] Deploy to Render/Railway/EC2"""

chk_new = """### Phase 6: Enterprise Deployment & Submission (Priority 4)

- [ ] Set up `docker-compose.yml` with NGINX, Redis, RabbitMQ, API, and Workers
- [ ] Configure `nginx.conf` for reverse proxying and rate limiting
- [ ] Create `Dockerfile` (python:3.12-slim based)
- [ ] Create `.env.example` with all required variable names
- [ ] Test Docker Compose build & run locally
- [ ] Deploy stack to EC2 / DigitalOcean"""

content = content.replace(chk_old, chk_new)


with open("/Users/nayburrahman/Documents/Sust-Hack-Mythos-1/HLD.md", "w") as f:
    f.write(content)

print("Replacement complete.")
