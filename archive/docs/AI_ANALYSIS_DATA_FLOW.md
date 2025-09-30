# AI Analysis Data Flow - Sequence Diagram

This document shows the complete data flow from user request to AI comments display, based on actual implementation analysis.

## Overview

The AI analysis system uses a **two-table architecture** with async background processing. AI comments are stored in database and sent to frontend, but frontend display is incomplete.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as Backend API
    participant Service as AnalysisService
    participant Repo as Repository
    participant DB as Database
    participant AI as AI Orchestrator
    participant LangGraph as LangGraph Agents

    Note over User, LangGraph: 1. Analysis Request Flow
    User->>Frontend: Upload resume & request analysis
    Frontend->>API: POST /api/v1/analysis/request
    API->>Service: request_analysis(resume_id, industry)

    Note over Service: Validate industry support
    Service->>Service: map_database_industry_to_ai_agent()
    Note over Service: ma_financial → finance_banking

    Service->>Repo: create_analysis()
    Repo->>DB: INSERT review_requests (status: pending)
    DB-->>Repo: review_request created

    Service->>Service: _queue_analysis_job() (async task)
    Service-->>API: AnalysisResponse(analysis_id, status: pending)
    API-->>Frontend: 201 Created {analysis_id, status: pending}
    Frontend-->>User: "Analysis started, please wait..."

    Note over User, LangGraph: 2. Background AI Processing
    par Background Processing
        Service->>Repo: update_status(processing)
        Repo->>DB: UPDATE review_requests SET status='processing'

        Service->>AI: analyze(resume_text, finance_banking, analysis_id)
        AI->>LangGraph: Structure Agent → Appeal Agent

        Note over LangGraph: AI Analysis Processing
        LangGraph->>LangGraph: Structure Analysis
        Note over LangGraph: Issues: ["No resume format", "No organization"]<br/>Recommendations: ["Use standard template", "Add sections"]<br/>Missing: ["Contact Info", "Experience", "Education"]

        LangGraph->>LangGraph: Appeal Analysis
        Note over LangGraph: Skills alignment, achievements, experience fit

        LangGraph-->>AI: Complete AI Response
        Note over AI: {<br/>  "success": true,<br/>  "overall_score": 0.0,<br/>  "summary": "Resume scores 0/100...",<br/>  "structure": {<br/>    "feedback": {<br/>      "issues": ["Document not resume format"],<br/>      "recommendations": ["Start with template"],<br/>      "missing_sections": ["All sections missing"]<br/>    }<br/>  },<br/>  "appeal": { feedback... }<br/>}

        AI-->>Service: AI Analysis Result

        Note over Service: Convert AI Response to Database Format
        Service->>Service: _store_analysis_results()
        Service->>Service: _convert_score_to_int() & _create_detailed_scores()

        Service->>Repo: save_results()
        Repo->>DB: INSERT review_results<br/>(overall_score: 0, detailed_scores: JSON)
        Note over DB: detailed_scores = {<br/>  "structure_analysis": {<br/>    "feedback": {<br/>      "issues": ["Document not resume format"],<br/>      "recommendations": ["Start with template"],<br/>      "missing_sections": ["All sections"]<br/>    }<br/>  }<br/>}

        Service->>Repo: update_status(completed)
        Repo->>DB: UPDATE review_requests SET status='completed'
    end

    Note over User, LangGraph: 3. Frontend Polling & Result Retrieval
    loop Every 3 seconds
        Frontend->>API: GET /api/v1/analysis/{id}/status
        API->>Service: get_analysis_status(analysis_id, user_id)
        Service->>Repo: get_analysis_with_results(analysis_id)
        Repo->>DB: SELECT review_requests JOIN review_results
        DB-->>Repo: (request, result) data

        Service->>Service: _build_result_response(request, result)
        Note over Service: Returns: {<br/>  "analysis_id": "uuid",<br/>  "overall_score": 0,<br/>  "executive_summary": "Resume scores 0/100...",<br/>  "detailed_scores": {<br/>    "structure_analysis": {<br/>      "feedback": {<br/>        "issues": [...],<br/>        "recommendations": [...],<br/>        "missing_sections": [...]<br/>      }<br/>    }<br/>  }<br/>}

        Service-->>API: AnalysisStatusResponse
        API-->>Frontend: 200 OK with complete data

        alt Status: completed
            Frontend->>Frontend: Parse response data
            Note over Frontend: ❌ ISSUE: Only shows overall_score<br/>❌ NOT parsing detailed_scores.structure_analysis.feedback<br/>❌ AI comments NOT displayed to user
            Frontend-->>User: Shows only: "Score: 0/100" + summary
        else Status: pending/processing
            Frontend-->>User: "Still processing..."
        end
    end

    Note over User, LangGraph: 4. Current Problem Areas

    rect rgb(255, 200, 200)
        Note over Frontend: MISSING: AI Comments Display<br/>• Issues not shown<br/>• Recommendations not shown<br/>• Missing sections not shown<br/>• Strengths not shown
    end

    rect rgb(200, 255, 200)
        Note over DB, AI: ✅ WORKING PERFECTLY<br/>• AI generates detailed comments<br/>• Comments stored in database<br/>• Comments sent to frontend<br/>• Backend API complete
    end
```

## Data Structure at Each Stage

### 1. AI Orchestrator Response
```json
{
  "success": true,
  "analysis_id": "uuid",
  "overall_score": 75.0,
  "market_tier": "mid",
  "summary": "Executive summary of analysis...",
  "structure": {
    "scores": {"format": 80, "organization": 75, "tone": 70, "completeness": 85},
    "feedback": {
      "issues": ["Inconsistent bullet points", "Poor section separation"],
      "recommendations": ["Add contact section", "Use consistent bullets"],
      "missing_sections": ["Contact Information", "Education section"],
      "strengths": ["Good work experience details"]
    }
  },
  "appeal": {
    "scores": {"achievement_relevance": 78, "skills_alignment": 72},
    "feedback": {
      "relevant_achievements": ["Led team of 8 developers"],
      "missing_skills": ["Cloud architecture", "DevOps"],
      "competitive_advantages": ["Strong technical leadership"],
      "improvement_areas": ["Add more quantified results"]
    }
  }
}
```

### 2. Database Storage (review_results table)
```sql
overall_score: 75
ats_score: 80
content_score: 78
formatting_score: 85
executive_summary: "Executive summary of analysis..."
detailed_scores: {
  "structure_analysis": {
    "scores": {"format": 80, "organization": 75, "tone": 70, "completeness": 85},
    "feedback": {
      "issues": ["Inconsistent bullet points", "Poor section separation"],
      "recommendations": ["Add contact section", "Use consistent bullets"],
      "missing_sections": ["Contact Information", "Education section"],
      "strengths": ["Good work experience details"]
    }
  },
  "appeal_analysis": {
    "scores": {"achievement_relevance": 78, "skills_alignment": 72},
    "feedback": {
      "relevant_achievements": ["Led team of 8 developers"],
      "missing_skills": ["Cloud architecture", "DevOps"],
      "competitive_advantages": ["Strong technical leadership"],
      "improvement_areas": ["Add more quantified results"]
    }
  },
  "market_tier": "mid",
  "ai_analysis_id": "uuid",
  "conversion_timestamp": "2025-09-28T00:44:20.894993+00:00"
}
```

### 3. Backend API Response to Frontend
```json
{
  "analysis_id": "uuid",
  "status": "completed",
  "requested_at": "2025-09-28T00:43:58.706Z",
  "completed_at": "2025-09-28T00:44:20.906Z",
  "result": {
    "analysis_id": "uuid",
    "overall_score": 75,
    "ats_score": 80,
    "content_score": 78,
    "formatting_score": 85,
    "industry": "strategy_tech",
    "executive_summary": "Executive summary of analysis...",
    "detailed_scores": {
      "structure_analysis": {
        "feedback": {
          "issues": ["Inconsistent bullet points", "Poor section separation"],
          "recommendations": ["Add contact section", "Use consistent bullets"],
          "missing_sections": ["Contact Information", "Education section"],
          "strengths": ["Good work experience details"]
        }
      },
      "appeal_analysis": {
        "feedback": {
          "relevant_achievements": ["Led team of 8 developers"],
          "missing_skills": ["Cloud architecture", "DevOps"],
          "competitive_advantages": ["Strong technical leadership"],
          "improvement_areas": ["Add more quantified results"]
        }
      }
    },
    "ai_model_used": "gpt-4",
    "processing_time_ms": 30000,
    "completed_at": "2025-09-28T00:44:20.906Z"
  }
}
```

### 4. What Frontend Currently Shows vs What's Available

#### ✅ Currently Displayed:
- Overall score (75)
- Executive summary ("Executive summary of analysis...")

#### ❌ Available But NOT Displayed:
- **Issues**: ["Inconsistent bullet points", "Poor section separation"]
- **Recommendations**: ["Add contact section", "Use consistent bullets"]
- **Missing Sections**: ["Contact Information", "Education section"]
- **Strengths**: ["Good work experience details"]
- **Missing Skills**: ["Cloud architecture", "DevOps"]
- **Competitive Advantages**: ["Strong technical leadership"]
- **Improvement Areas**: ["Add more quantified results"]
- **Relevant Achievements**: ["Led team of 8 developers"]

## Solution Required

### Backend: ✅ Complete (No changes needed)
- AI comments are generated correctly
- Data is stored in database properly
- API returns complete data including `detailed_scores`

### Frontend: ❌ Incomplete (Needs enhancement)
The frontend needs to:

1. **Parse `detailed_scores`** from the API response
2. **Extract comment arrays** from the nested JSON structure
3. **Add UI components** to display:
   - Issues section
   - Recommendations section
   - Missing sections
   - Strengths (when available)
   - Missing skills
   - Improvement areas
   - Competitive advantages

### Example Frontend Enhancement Needed:
```javascript
// Parse the detailed_scores from API response
const { detailed_scores } = analysisResult.result;
const structureFeedback = detailed_scores?.structure_analysis?.feedback || {};
const appealFeedback = detailed_scores?.appeal_analysis?.feedback || {};

// Display the AI comments
const issues = structureFeedback.issues || [];
const recommendations = structureFeedback.recommendations || [];
const missingSkills = appealFeedback.missing_skills || [];
const strengths = structureFeedback.strengths || [];
```

## Conclusion

The **AI analysis system is working perfectly**. All AI comments are generated, stored, and sent to the frontend. The only missing piece is **frontend parsing and display** of the rich feedback data that's already available in the `detailed_scores` field.