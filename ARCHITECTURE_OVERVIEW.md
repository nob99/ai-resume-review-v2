# AI Resume Review Platform - Architecture Overview

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                           User Interface                        │
│                         (Web Browser)                          │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                            │
│                   (Cloud Run Service)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Login     │  │   Upload    │  │   History   │            │
│  │    Page     │  │    Page     │  │    Page     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ REST API (JSON)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                              │
│                   (Cloud Run Service)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Auth     │  │    File     │  │  AI Agent   │            │
│  │   Handler   │  │  Processor  │  │ Orchestrator│            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                    ┌─────────────┐            │
│                                    │ LangChain/  │            │
│                                    │ LangGraph   │            │
│                                    └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │ SQL Queries
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                           │
│                   (Cloud SQL)                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Users    │  │  Analyses   │  │  Results    │            │
│  │    Table    │  │   Table     │  │   Table     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘

External Services:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenAI API    │    │ Secret Manager  │    │ Cloud Logging   │
│     (GPT-5)     │    │  (API Keys)     │    │  (Monitoring)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 2. Component Responsibilities

### 2.1 Frontend (Next.js)
- **Purpose**: User interface for consultants
- **Responsibilities**:
  - User authentication (login/logout)
  - Resume upload interface
  - Display AI analysis results
  - User management (admin only)
  - History browsing
- **Technology**: Next.js, React, TypeScript
- **Deployment**: Cloud Run container

### 2.2 Backend (FastAPI)
- **Purpose**: API server and AI processing
- **Responsibilities**:
  - REST API endpoints
  - JWT authentication
  - File processing (PDF/DOCX parsing)
  - AI agent orchestration
  - Database operations
  - Result generation (XML)
- **Technology**: FastAPI, Python, LangChain/LangGraph
- **Deployment**: Cloud Run container

### 2.3 Database (PostgreSQL)
- **Purpose**: Data persistence
- **Responsibilities**:
  - User account management
  - Analysis session tracking
  - Result storage (XML)
  - Configuration data
- **Technology**: PostgreSQL 15
- **Deployment**: Cloud SQL instance

### 2.4 AI Agents
- **Structure Agent**: General resume quality analysis
- **Appeal Point Agent**: Industry-specific evaluation
- **Technology**: LangChain/LangGraph with OpenAI GPT-5

## 3. Data Flow

### 3.1 Resume Analysis Flow
```
1. User uploads resume via frontend
2. Frontend sends multipart form to backend API
3. Backend validates file and extracts text
4. Backend calls Structure Agent (LLM)
5. Backend calls Appeal Point Agent (LLM) with industry context
6. Backend combines results into XML
7. Backend stores results in database
8. Backend returns XML to frontend
9. Frontend displays parsed results to user
10. User can download results as PDF/TXT
```

### 3.2 Authentication Flow
```
1. User submits credentials via frontend
2. Frontend sends login request to backend API
3. Backend validates against database
4. Backend generates JWT token
5. Backend sets httpOnly cookie in response
6. Frontend stores authentication state
7. Subsequent requests include cookie automatically
8. Backend validates JWT on each protected endpoint
```

## 4. Project Folder Structure

```
ai-resume-review-v2/
├── README.md
├── PRODUCT_VISION.md
├── ARCHITECTURE_OVERVIEW.md
├── requirements/
│   ├── 01_UI_UX_REQUIREMENTS.md
│   ├── 02_BACKEND_REQUIREMENTS.md
│   ├── 03_DATABASE_REQUIREMENTS.md
│   ├── 04_API_REQUIREMENTS.md
│   └── 05_INFRASTRUCTURE_REQUIREMENTS.md
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── src/
│   │   ├── pages/
│   │   │   ├── login.tsx
│   │   │   ├── index.tsx          # Upload/Home page
│   │   │   ├── history.tsx
│   │   │   └── admin/
│   │   │       └── users.tsx
│   │   ├── components/
│   │   │   ├── Layout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── UploadForm.tsx
│   │   │   ├── ResultsDisplay.tsx
│   │   │   └── AnalysisHistory.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useAnalysis.ts
│   │   │   └── useApi.ts
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   ├── auth.ts
│   │   │   ├── analysis.ts
│   │   │   └── api.ts
│   │   └── styles/
│   │       └── globals.css
│   └── public/
│       └── favicon.ico
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Environment configuration
│   ├── database.py                # Database connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                # User SQLAlchemy model
│   │   ├── analysis.py            # Analysis SQLAlchemy model
│   │   └── industry.py            # Industry SQLAlchemy model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                # Pydantic auth schemas
│   │   ├── analysis.py            # Pydantic analysis schemas
│   │   └── user.py                # Pydantic user schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                # Authentication endpoints
│   │   ├── analyses.py            # Resume analysis endpoints
│   │   ├── users.py               # User management endpoints
│   │   └── health.py              # Health check endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py        # JWT and authentication logic
│   │   ├── file_processor.py      # PDF/DOCX text extraction
│   │   ├── ai_orchestrator.py     # LangChain/LangGraph workflows
│   │   └── result_formatter.py    # XML generation and formatting
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── structure_agent.py     # Structure review agent
│   │   ├── appeal_agent.py        # Appeal point agent
│   │   └── base_agent.py          # Common agent functionality
│   ├── prompts/
│   │   ├── structure_prompt.txt   # Structure agent prompt
│   │   ├── appeal_prompts/
│   │   │   ├── strategy_consulting.txt
│   │   │   ├── technology_consulting.txt
│   │   │   ├── ma_consulting.txt
│   │   │   ├── financial_advisory.txt
│   │   │   ├── full_service_consulting.txt
│   │   │   └── system_integrator.txt
│   │   └── prompt_loader.py       # Dynamic prompt loading
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── security.py            # Password hashing, JWT utils
│   │   ├── exceptions.py          # Custom exception classes
│   │   └── logging.py             # Logging configuration
│   └── tests/
│       ├── __init__.py
│       ├── test_auth.py
│       ├── test_analysis.py
│       └── test_agents.py
├── database/
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_seed_industries.sql
│   │   └── 003_create_admin_user.sql
│   └── scripts/
│       ├── setup_database.sh
│       └── create_users.sql
├── deployment/
│   ├── frontend.Dockerfile
│   ├── backend.Dockerfile
│   ├── docker-compose.yml        # Local development
│   ├── deploy-frontend.sh        # GCP deployment script
│   ├── deploy-backend.sh         # GCP deployment script
│   └── setup-infrastructure.sh   # Initial GCP setup
└── docs/
    ├── api-documentation.md      # Detailed API docs
    ├── deployment-guide.md       # Step-by-step deployment
    └── development-setup.md      # Local development guide
```

## 5. Technology Stack Summary

### 5.1 Frontend Stack
- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS (blue theme)
- **State Management**: React hooks + Context API
- **HTTP Client**: Fetch API with custom hooks
- **Authentication**: Cookie-based JWT
- **Build Tool**: Next.js built-in bundler

### 5.2 Backend Stack
- **Framework**: FastAPI with Python 3.11+
- **ORM**: SQLAlchemy with async support
- **Validation**: Pydantic models
- **Authentication**: JWT with passlib
- **AI Framework**: LangChain/LangGraph
- **LLM Provider**: OpenAI (GPT-5)
- **File Processing**: PyPDF2, python-docx
- **Testing**: pytest with async support

### 5.3 Infrastructure Stack
- **Platform**: Google Cloud Platform
- **Compute**: Cloud Run (serverless containers)
- **Database**: Cloud SQL PostgreSQL 15
- **Secrets**: Secret Manager
- **Monitoring**: Cloud Logging
- **Networking**: Private IPs, HTTPS
- **Deployment**: gcloud CLI

## 6. Development Workflow

### 6.1 Local Development
1. Clone repository
2. Set up PostgreSQL database locally
3. Install frontend dependencies: `cd frontend && npm install`
4. Install backend dependencies: `cd backend && pip install -r requirements.txt`
5. Run database migrations
6. Start backend: `cd backend && uvicorn main:app --reload`
7. Start frontend: `cd frontend && npm run dev`
8. Access application at http://localhost:3000

### 6.2 Deployment Process
1. Build Docker images for frontend and backend
2. Push images to Google Container Registry
3. Deploy to Cloud Run using gcloud CLI
4. Update environment variables and secrets
5. Run database migrations on Cloud SQL
6. Verify deployment with health checks

## 7. Security Architecture

### 7.1 Network Security
- HTTPS everywhere (automatic with Cloud Run)
- Database on private IP (no public access)
- Service-to-service communication within GCP network

### 7.2 Application Security
- JWT tokens in httpOnly cookies
- Password hashing with bcrypt
- Input validation on all endpoints
- CORS restrictions to frontend domain only
- Rate limiting to prevent abuse

### 7.3 Data Security
- API keys stored in Secret Manager
- No resume text stored in database
- Database credentials in environment variables
- Minimal service account permissions

This architecture provides a solid foundation for the MVP while maintaining simplicity and allowing for future scalability.