# AI Resume Review Platform - Architecture Document

## 1. Overview

This document outlines the technical architecture for the AI Resume Review Platform MVP. The system is designed to be simple, scalable, and secure, focusing on delivering core functionality while maintaining flexibility for future enhancements.

## 2. Architecture Principles

- **Simplicity First**: Start small, iterate based on feedback
- **Separation of Concerns**: Clear boundaries between layers
- **Stateless Design**: No session state in AI processing
- **Security by Default**: No persistent file storage, encrypted communications
- **Cloud-Native**: Leverage managed services for reliability

## 3. High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Next.js App   │────▶│  FastAPI Backend│────▶│  AI Agents      │
│   (Frontend)    │     │  (API Layer)    │     │  (LangChain)    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐             │
         │              │                 │             │
         └─────────────▶│   PostgreSQL    │◀────────────┘
                        │   (Cloud SQL)    │
                        │                 │
                        └─────────────────┘
```

## 4. Component Architecture

### 4.1 Frontend (Next.js)

```
frontend/
├── app/                    # Next.js 14 app directory
│   ├── (auth)/            # Auth-protected routes
│   │   ├── dashboard/     # Main dashboard
│   │   ├── analyze/       # Resume analysis page
│   │   └── results/       # Results display
│   ├── admin/             # Admin routes
│   │   └── prompts/       # Prompt management
│   └── login/             # Public login page
├── components/
│   ├── ui/                # Reusable UI components
│   ├── FileUpload.tsx     # Resume upload component
│   ├── ResultsDisplay.tsx # Analysis results component
│   └── PromptEditor.tsx   # Admin prompt editor
├── lib/
│   ├── api.ts            # API client
│   └── auth.ts           # Auth utilities
└── contexts/
    └── AuthContext.tsx    # Authentication state
```

**Key Technologies:**
- Next.js 14 with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- React Context for state management
- Axios for API calls

### 4.2 Backend (FastAPI)

```
backend/
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── routers/
│   │       │   ├── auth.py      # Authentication endpoints
│   │       │   ├── resume.py    # Resume analysis endpoints
│   │       │   └── admin.py     # Admin endpoints
│   │       └── dependencies.py  # Shared dependencies
│   ├── core/
│   │   ├── config.py     # Configuration settings
│   │   ├── security.py   # Security utilities
│   │   └── database.py   # Database connection
│   ├── services/
│   │   ├── auth_service.py      # Authentication logic
│   │   ├── file_processor.py    # File handling & extraction
│   │   ├── ai_orchestrator.py   # AI agent coordination
│   │   └── prompt_service.py    # Prompt management
│   ├── agents/
│   │   ├── base_agent.py        # Base agent class
│   │   ├── structure_agent.py   # Basic structure analysis
│   │   └── appeal_agent.py      # Industry-specific analysis
│   ├── models/
│   │   ├── user.py              # User model
│   │   ├── analysis.py          # Analysis models
│   │   └── prompt.py            # Prompt models
│   └── schemas/
│       ├── auth.py              # Auth request/response schemas
│       ├── resume.py            # Resume analysis schemas
│       └── admin.py             # Admin schemas
```

**API Endpoints:**
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Current user info
- `POST /api/v1/resume/analyze` - Submit resume for analysis
- `GET /api/v1/resume/results/{id}` - Get analysis results
- `GET /api/v1/admin/prompts` - List prompts (admin)
- `PUT /api/v1/admin/prompts/{id}` - Update prompt (admin)
- `POST /api/v1/admin/prompts/test` - Test prompt (admin)

### 4.3 AI Agent Architecture (LangChain/LangGraph)

```python
# Agent Flow using LangGraph
┌─────────────────┐
│  File Upload    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Text Extraction │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Structure Agent │──── Analyzes format, tone, sections
└────────┬────────┘
         ▼
┌─────────────────┐
│  Appeal Agent   │──── Industry-specific analysis
└────────┬────────┘
         ▼
┌─────────────────┐
│ Result Aggregator│
└────────┬────────┘
         ▼
┌─────────────────┐
│  Save Results   │
└─────────────────┘
```

**Agent Components:**
- **Base Agent**: Abstract class with common functionality
- **Structure Agent**: General resume quality assessment
- **Appeal Agent**: Industry-specific evaluation
- **Orchestrator**: Manages agent workflow and state

## 5. Database Schema

### 5.1 Core Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'consultant',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis requests
CREATE TABLE analysis_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    industry VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Analysis results
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID REFERENCES analysis_requests(id),
    agent_type VARCHAR(50) NOT NULL,
    overall_score DECIMAL(3,2),
    scores JSONB,
    comments JSONB,
    recommendations JSONB,
    source_references JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Prompts table
CREATE TABLE prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry VARCHAR(100) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(industry, agent_type, is_active)
);

-- Prompt history
CREATE TABLE prompt_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_id UUID REFERENCES prompts(id),
    content TEXT NOT NULL,
    version INTEGER NOT NULL,
    changed_by UUID REFERENCES users(id),
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. Infrastructure Architecture

### 6.1 Google Cloud Platform Setup

```
┌─────────────────────────────────────────────────┐
│                   Cloud Load Balancer           │
└─────────────────────────┬───────────────────────┘
                          │
┌─────────────────────────▼───────────────────────┐
│                   Cloud Run                      │
│  ┌─────────────┐  ┌─────────────┐              │
│  │  Frontend   │  │   Backend   │              │
│  │  Container  │  │  Container  │              │
│  └─────────────┘  └─────────────┘              │
└─────────────────────────┬───────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         │                                 │
┌────────▼────────┐              ┌────────▼────────┐
│   Cloud SQL     │              │ Secret Manager  │
│  (PostgreSQL)   │              │  (API Keys)     │
└─────────────────┘              └─────────────────┘
```

### 6.2 Deployment Configuration

**Frontend (Cloud Run)**
- Container: Node.js 20 Alpine
- Memory: 256MB
- CPU: 1
- Min instances: 1
- Max instances: 10

**Backend (Cloud Run)**
- Container: Python 3.11 Slim
- Memory: 1GB
- CPU: 2
- Min instances: 1
- Max instances: 20

**Database (Cloud SQL)**
- PostgreSQL 15
- Instance: db-f1-micro (MVP)
- Storage: 10GB SSD
- Backup: Daily automated

## 7. Security Architecture

### 7.1 Authentication & Authorization

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    User      │────▶│   Frontend   │────▶│   Backend    │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │                     │
       │   Credentials       │    JWT Token       │
       └─────────────────────┴─────────────────────┘
```

- **Authentication**: JWT tokens with refresh tokens
- **Password Storage**: Bcrypt hashing
- **Session Management**: Stateless with token expiration
- **Role-Based Access**: Consultant vs Admin roles

### 7.2 Data Security

- **Transport**: HTTPS everywhere
- **Database**: Encrypted at rest
- **Files**: Temporary processing only, deleted after analysis
- **API Keys**: Stored in Google Secret Manager
- **Input Validation**: Pydantic models for all inputs

## 8. AI Integration Details

### 8.1 LangChain Configuration

```python
# Example agent configuration
class StructureAgent:
    def __init__(self, llm_model="gpt-4"):
        self.llm = ChatOpenAI(model=llm_model)
        self.prompt_template = PromptTemplate(
            template=load_prompt("structure_agent", industry)
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
    
    async def analyze(self, resume_text: str) -> AnalysisResult:
        # Analysis logic
        pass
```

### 8.2 Agent Communication Flow

1. **Input**: Resume text + Industry selection
2. **Structure Agent**: Analyzes format, completeness, professionalism
3. **Context Passing**: Structure results passed to Appeal Agent
4. **Appeal Agent**: Industry-specific evaluation using context
5. **Aggregation**: Combine results into final report

## 9. Development & Deployment

### 9.1 Local Development

```bash
# Frontend
cd frontend
npm install
npm run dev  # Runs on http://localhost:3000

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # Runs on http://localhost:8000
```

### 9.2 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
- Run tests
- Build Docker images
- Push to Artifact Registry
- Deploy to Cloud Run
- Run health checks
```

## 10. Monitoring & Observability

- **Application Monitoring**: Google Cloud Monitoring
- **Logs**: Cloud Logging with structured logs
- **Errors**: Sentry integration
- **Performance**: Cloud Trace for latency tracking
- **Uptime**: Cloud Monitoring uptime checks

## 11. Scalability Considerations

### 11.1 Current (MVP)
- Single-region deployment
- Synchronous processing
- Basic caching

### 11.2 Future Scaling Options
- Multi-region deployment
- Queue-based async processing
- Redis caching layer
- CDN for static assets
- Horizontal scaling for AI agents

## 12. Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14, TypeScript | Modern React framework |
| Backend | FastAPI, Python 3.11 | High-performance API |
| AI/ML | LangChain, OpenAI/Claude | Agent orchestration |
| Database | PostgreSQL 15 | Reliable data storage |
| Infrastructure | Google Cloud Platform | Managed cloud services |
| Deployment | Cloud Run, Docker | Container orchestration |
| Monitoring | Cloud Monitoring, Sentry | Observability |

## 13. Key Architecture Decisions

1. **Stateless Design**: Each request independent, no server-side sessions
2. **Microservices Ready**: Clean separation allows future service splitting
3. **Database-Driven Prompts**: Easy updates without code deployment
4. **Temporary File Processing**: Security-first approach
5. **Managed Services**: Reduce operational overhead
6. **API-First**: Clear contract between frontend and backend

## 14. Future Architecture Considerations

- **Batch Processing**: For multiple resume analysis
- **Webhook Integration**: For ATS system integration
- **Multi-Language Support**: i18n architecture preparation
- **Advanced Analytics**: Data warehouse for insights
- **API Gateway**: For rate limiting and API management

---

This architecture is designed to support the MVP requirements while providing a solid foundation for future growth and feature additions.