# AI Resume Review Platform - Product Vision Document

## 1. Product Overview
**Product Name**: AI Resume Review Platform  
**Version**: MVP (Minimum Viable Product)  
**Date**: November 2024

## 2. Problem Statement
Recruitment consultants spend significant time manually reviewing candidate resumes. They possess valuable domain expertise about what makes effective resumes for specific industries, but this knowledge is not scalable across high volumes of applications.

## 3. Solution
An AI-powered platform where multiple specialized AI agents automatically review candidate resumes, replicating consultant expertise to provide structured feedback on resume quality and industry-specific appeal points.

## 4. Core Value Proposition
- **Efficiency**: Automate time-consuming resume review process
- **Consistency**: Standardized evaluation across all resumes
- **Expertise**: Industry-specific insights embedded in AI agents
- **Scalability**: Handle high volumes without additional resources

## 5. Target Users
Primary: Recruitment consultants at recruitment agencies who need to review multiple resumes daily

## 6. Key Features (MVP)

### 6.1 Multi-Agent Resume Analysis
- **Basic Structure Agent**: Reviews general resume quality
  - Format consistency
  - Professional tone
  - Section organization
  - Completeness
  
- **Appeal Point Agent**: Industry-specific evaluation
  - Relevant achievements
  - Industry-aligned skills
  - Experience fit
  - Competitive positioning

### 6.2 Supported Industries (Initial)
1. Strategy Consulting
2. Technology Consulting
3. M&A Consulting
4. Financial Advisory Consulting
5. Full Service Consulting
6. System Integrator

### 6.3 Core Workflow
1. Consultant logs into web platform
2. Uploads candidate resume (PDF/Word)
3. Selects target industry
4. AI agents analyze resume sequentially
5. View structured results with scores, comments, recommendations, and source references
6. Use insights for candidate feedback (offline)

## 7. Technical Approach
- **Frontend**: Next.js web application
- **Backend**: FastAPI Python service
- **AI Framework**: LangChain/LangGraph
- **Database**: Cloud SQL (PostgreSQL)
- **Infrastructure**: Google Cloud Platform (Cloud Run)
- **Principles**: Small start, simple architecture, scalable design

## 8. Success Criteria
- Consultants can review resumes 80% faster
- Consistent evaluation quality across all resumes
- Easy to add new industries and evaluation criteria
- Reliable and secure platform

## 9. Out of Scope (MVP)
- File storage (security consideration)
- Automated candidate communication
- Resume editing/improvement features
- Multi-language support
- Mobile application

## 10. Future Vision
- Expand to more industries
- Add specialized agents (technical skills, cultural fit)
- Batch processing capabilities
- Analytics and insights dashboard
- API for integration with ATS systems

---

This document represents our agreed product vision.