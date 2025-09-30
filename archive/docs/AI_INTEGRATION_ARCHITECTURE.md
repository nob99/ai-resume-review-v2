# AI Integration Architecture - Resume Review System

**Date**: September 9, 2025  
**Version**: 1.0  
**Status**: Ready for Implementation

## 📋 Executive Summary

This document outlines the integration architecture between the AI agents system and the new candidate-centric database schema (v1.1). The integration enables AI-powered resume analysis through a structured workflow that processes review requests and stores detailed feedback.

---

## 🏗️ System Architecture Overview

### Core Components

1. **AI Agents Module** (`ai_agents/`)
   - LangGraph-based orchestration system
   - Two-agent pipeline: Structure Agent → Appeal Agent
   - Async-compatible with built-in error handling

2. **Database Schema** (v1.1)
   - `ReviewRequest` → `ReviewResult` + `ReviewFeedbackItem`
   - Candidate-centric with role-based access control
   - Section-level feedback support

3. **Integration Layer** (To be implemented)
   - ReviewService: Business logic orchestration
   - AIIntegrationService: AI-to-database mapping
   - ReviewRepository: Database operations

---

## 🔄 Data Flow Architecture

```
1. User requests review for candidate's resume
   ↓
2. ReviewService creates ReviewRequest record
   ↓
3. Background task triggered for processing
   ↓
4. Fetch resume text from Resume table
   ↓
5. Call AI Orchestrator with resume + industry
   ↓
6. AI Agents analyze (Structure → Appeal)
   ↓
7. Map AI results to database models
   ↓
8. Store ReviewResult + ReviewFeedbackItems
   ↓
9. Update ReviewRequest status to completed
   ↓
10. Return results to frontend
```

---

## 🤖 AI Agents System

### Orchestrator Interface

```python
orchestrator = ResumeAnalysisOrchestrator()
result = await orchestrator.analyze(
    resume_text=str,      # From Resume.extracted_text
    industry=str,         # From ReviewRequest.target_industry
    analysis_id=str       # From ReviewRequest.id
)
```

### Response Format

```json
{
  "success": true,
  "analysis_id": "uuid",
  "overall_score": 85.5,
  "market_tier": "senior",
  "summary": "Executive summary...",
  "structure": {
    "scores": {
      "format": 90,
      "organization": 85,
      "tone": 88,
      "completeness": 92
    },
    "feedback": {
      "issues": [...],
      "missing_sections": [...],
      "strengths": [...],
      "recommendations": [...]
    },
    "metadata": {
      "total_sections": 8,
      "word_count": 450
    }
  },
  "appeal": {
    "scores": {
      "achievement_relevance": 87,
      "skills_alignment": 82,
      "experience_fit": 90,
      "competitive_positioning": 85
    },
    "feedback": {
      "relevant_achievements": [...],
      "missing_skills": [...],
      "improvement_areas": [...]
    }
  }
}
```

### Supported Industries

- `tech_consulting` - Technology Consulting
- `finance_banking` - Finance & Banking  
- `strategy_consulting` - Strategy Consulting
- `system_integrator` - Systems Integration
- `full_service_consulting` - Full Service Consulting
- `general_business` - General Business

---

## 📊 Database Schema Mapping

### ReviewRequest → AI Input

| Database Field | AI Agent Input | Mapping Logic |
|---------------|----------------|---------------|
| `resume_id` | - | Fetch Resume.extracted_text |
| `target_industry` | `industry` | Direct mapping with validation |
| `target_role` | - | Could enhance prompts (future) |
| `experience_level` | - | Could adjust scoring (future) |
| `review_type` | - | Could affect agent selection (future) |

### AI Output → ReviewResult

| AI Output | Database Field | Mapping Logic |
|-----------|----------------|---------------|
| `overall_score` | `overall_score` | Direct mapping |
| `structure.scores.format` | `formatting_score` | Direct mapping |
| `structure.scores.completeness` | `ats_score` | Direct mapping |
| `appeal.scores.achievement_relevance` | `content_score` | Direct mapping |
| `summary` | `executive_summary` | Direct mapping |
| All scores | `detailed_scores` (JSON) | Store complete structure |
| - | `ai_model_used` | From config (e.g., "gpt-4") |
| Processing time | `processing_time_ms` | Calculate from timestamps |

### AI Feedback → ReviewFeedbackItem

| AI Output | Database Field | Mapping Logic |
|-----------|----------------|---------------|
| Feedback list item | `feedback_text` | Individual item text |
| Feedback category | `feedback_type` | Map to: strength/weakness/suggestion |
| Source (structure/appeal) | `category` | Map to: content/formatting/keywords |
| - | `severity_level` | Derive from type (1-5 scale) |
| - | `confidence_score` | Default to 85 or from AI |
| - | `resume_section_id` | NULL (future enhancement) |
| - | `original_text` | NULL (not provided by AI) |
| - | `suggested_text` | NULL (not provided by AI) |

---

## 🛠️ Required Services & APIs

### 1. ReviewService (`app/features/review/service.py`)

**Responsibilities:**
- Orchestrate review workflow
- Manage review request lifecycle
- Handle async processing
- Enforce access control

**Key Methods:**
```python
async def create_review_request(
    resume_id: UUID,
    target_role: Optional[str],
    target_industry: str,
    experience_level: Optional[str],
    review_type: str,
    user_id: UUID
) -> ReviewRequest

async def process_review(
    review_request_id: UUID
) -> ReviewResult

async def get_review_results(
    review_request_id: UUID,
    user_id: UUID
) -> Dict[str, Any]
```

### 2. AIIntegrationService (`app/features/review/ai_integration.py`)

**Responsibilities:**
- Interface with AI agents
- Transform data formats
- Handle AI errors gracefully
- Map results to database schema

**Key Methods:**
```python
async def analyze_resume(
    resume_text: str,
    industry: str,
    review_request_id: UUID
) -> Dict[str, Any]

def map_ai_to_database(
    ai_result: Dict[str, Any],
    review_request_id: UUID
) -> Tuple[Dict, List[Dict]]

def extract_feedback_items(
    ai_result: Dict[str, Any]
) -> List[Dict[str, Any]]
```

### 3. ReviewRepository (`app/features/review/repository.py`)

**Responsibilities:**
- Database CRUD operations
- Transaction management
- Query optimization
- Data integrity

**Key Methods:**
```python
async def create_review_request(**kwargs) -> ReviewRequest
async def update_request_status(id: UUID, status: str) -> None
async def create_review_result(**kwargs) -> ReviewResult
async def bulk_create_feedback_items(items: List) -> List[ReviewFeedbackItem]
async def get_review_with_feedback(id: UUID) -> Dict
```

### 4. API Endpoints (`app/features/review/api.py`)

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reviews/request` | Create new review request |
| GET | `/reviews/{id}` | Get review status |
| GET | `/reviews/{id}/results` | Get review results with feedback |
| GET | `/candidates/{id}/reviews` | List reviews for a candidate |
| POST | `/reviews/{id}/process` | Trigger review processing |
| GET | `/reviews/{id}/feedback` | Get detailed feedback items |

---

## ⚠️ Implementation Considerations

### Performance
- AI analysis target: < 60 seconds
- Use background tasks for processing
- Consider queue system for scalability
- Cache results for repeated requests

### Error Handling
- AI agents have built-in retry logic
- Graceful degradation on partial failures
- Store error state in ReviewRequest.status
- Provide meaningful error messages to users

### Security
- Validate industry codes against whitelist
- Sanitize resume text before AI processing
- Rate limit review requests per user
- Audit trail for all review requests

### Scalability
- Async processing throughout
- Database connection pooling
- Consider separate AI processing workers
- Implement request queuing for high load

---

## 📈 Future Enhancements

### Phase 1 (Current)
- ✅ Basic AI integration
- ✅ Store results in new schema
- ✅ Simple feedback mapping

### Phase 2 (Next Sprint)
- [ ] Section-level feedback mapping
- [ ] Enhanced prompt templates from database
- [ ] Batch processing support
- [ ] Review comparison features

### Phase 3 (Future)
- [ ] Custom industry configurations
- [ ] Multi-language support
- [ ] Advanced NLP for text suggestions
- [ ] Real-time processing status updates
- [ ] ML model for section detection

---

## 🔍 Testing Strategy

### Unit Tests
- Mock AI orchestrator responses
- Test data transformation logic
- Validate error handling

### Integration Tests
- End-to-end review workflow
- Database transaction integrity
- API endpoint validation

### Performance Tests
- Load testing with concurrent requests
- AI processing time benchmarks
- Database query optimization

---

## 📋 Implementation Checklist

- [ ] Create ReviewService with business logic
- [ ] Implement AIIntegrationService for AI bridge
- [ ] Build ReviewRepository for database ops
- [ ] Create API endpoints with proper validation
- [ ] Add background task processing
- [ ] Implement error handling and logging
- [ ] Write comprehensive tests
- [ ] Add monitoring and metrics
- [ ] Create API documentation
- [ ] Performance optimization

---

## 📚 Related Documentation

- `database/docs/schema_v1.1.md` - Database schema details
- `ai_agents/README.md` - AI agents system documentation
- `backend/app/DATABASE_MIGRATION_NOTES.md` - Migration guidance
- `backend/app/features/review/README.md` - Review feature docs (to be created)

---

*Last Updated: September 9, 2025*  
*Author: Backend Engineering Team*  
*Status: Ready for Implementation*