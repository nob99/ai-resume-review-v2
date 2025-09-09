# Backend Integration Test Plan - Schema v1.1

**Date**: September 9, 2025  
**Target**: FastAPI Backend + SQLAlchemy Integration  
**Database**: PostgreSQL 15 with Schema v1.1  
**Purpose**: Validate application layer compatibility with new database schema

## Overview

The database migration to Schema v1.1 is **complete**. This document provides a comprehensive test plan for backend engineers to validate that the FastAPI application works correctly with the new candidate-centric database structure.

### Migration Impact Summary
- ✅ **Database Schema**: Fully migrated and validated
- 🔄 **Backend Code**: Requires updates and testing
- ⏳ **API Endpoints**: Need validation with new schema
- ⏳ **Frontend**: Will require updates after backend integration

---

## **Phase 1: SQLAlchemy Model Updates & Testing**

### **1.1 Required Model Changes**

#### **New Models to Create:**
```python
# app/models/candidate.py
class Candidate(Base):
    __tablename__ = 'candidates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    current_company = Column(String(255))
    current_position = Column(String(255))  # Note: was current_role in draft
    years_experience = Column(Integer)
    status = Column(String(20), default='active')
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    created_by = relationship("User", back_populates="created_candidates")
    resumes = relationship("Resume", back_populates="candidate")
    assignments = relationship("UserCandidateAssignment", back_populates="candidate")

# app/models/user_candidate_assignment.py
class UserCandidateAssignment(Base):
    __tablename__ = 'user_candidate_assignments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)
    assignment_type = Column(String(20), default='primary')
    assigned_at = Column(TIMESTAMP(timezone=True), default=func.now())
    unassigned_at = Column(TIMESTAMP(timezone=True))
    assigned_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    unassigned_reason = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    candidate = relationship("Candidate", back_populates="assignments")
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])

# app/models/resume.py (replaces FileUpload)
class Resume(Base):
    __tablename__ = 'resumes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey('candidates.id'), nullable=False)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    version_number = Column(Integer, default=1)
    status = Column(String(20), default='pending')
    progress = Column(Integer, default=0)
    extracted_text = Column(Text)
    word_count = Column(Integer)
    uploaded_at = Column(TIMESTAMP(timezone=True), default=func.now())
    processed_at = Column(TIMESTAMP(timezone=True))
    
    # Relationships
    candidate = relationship("Candidate", back_populates="resumes")
    uploaded_by = relationship("User")
    sections = relationship("ResumeSection", back_populates="resume")
    review_requests = relationship("ReviewRequest", back_populates="resume")
```

#### **Models to Update:**
```python
# app/models/user.py - Update role enum
class User(Base):
    # ... existing fields ...
    role = Column(Enum('junior_recruiter', 'senior_recruiter', 'admin', name='user_roles'))
    
    # New relationships
    created_candidates = relationship("Candidate", back_populates="created_by")
    assignments = relationship("UserCandidateAssignment", foreign_keys="UserCandidateAssignment.user_id")

# app/models/prompt.py - Add agent_type
class Prompt(Base):
    # ... existing fields ...
    agent_type = Column(String(50))  # base_agent, structure_agent, appeal_agent
    variables = Column(JSON, default={})
    # Remove created_by relationship
```

### **1.2 Model Testing Checklist**

**Test Scenarios:**
- [ ] **Model Creation**: All new models can be instantiated
- [ ] **Relationships**: Foreign key relationships work correctly
- [ ] **Constraints**: Database constraints are enforced
- [ ] **Migrations**: Alembic migrations work with new models
- [ ] **Queries**: Basic CRUD operations work through ORM

**Test Commands:**
```bash
# Run model tests
pytest tests/models/ -v

# Test database connection
python -c "from app.database import get_db; print('DB connection OK')"

# Test model relationships
python -c "
from app.models import Candidate, User, Resume
# Test relationship queries
"
```

---

## **Phase 2: Service Layer Integration Testing**

### **2.1 Service Updates Required**

#### **New Services to Create:**
```python
# app/services/candidate_service.py
class CandidateService:
    def create_candidate(self, candidate_data: dict, created_by_user_id: UUID) -> Candidate:
        # Create candidate and auto-assign to creator
        pass
    
    def get_candidates_for_user(self, user_id: UUID, user_role: str) -> List[Candidate]:
        # Role-based candidate access
        if user_role == 'junior_recruiter':
            # Return only assigned candidates
            pass
        elif user_role in ['senior_recruiter', 'admin']:
            # Return all candidates
            pass
    
    def assign_candidate(self, candidate_id: UUID, user_id: UUID, assigned_by: UUID) -> UserCandidateAssignment:
        # Create new assignment, deactivate old ones
        pass

# app/services/resume_service.py (replaces file_upload_service.py)
class ResumeService:
    def upload_resume(self, candidate_id: UUID, file_data, uploaded_by_user_id: UUID) -> Resume:
        # Handle resume upload and processing
        pass
    
    def get_resumes_for_candidate(self, candidate_id: UUID, user_id: UUID) -> List[Resume]:
        # Check user has access to candidate first
        pass

# app/services/review_service.py (replaces analysis_service.py)  
class ReviewService:
    def request_review(self, resume_id: UUID, user_id: UUID, review_params: dict) -> ReviewRequest:
        # Create review request, validate access
        pass
    
    def process_review(self, review_request_id: UUID) -> ReviewResult:
        # Integrate with AI agents
        pass
```

#### **Services to Update:**
```python
# app/services/auth_service.py
class AuthService:
    def get_user_permissions(self, user: User) -> dict:
        # Return permissions based on new role structure
        return {
            'can_see_all_candidates': user.role in ['senior_recruiter', 'admin'],
            'can_assign_candidates': user.role in ['senior_recruiter', 'admin'], 
            'can_manage_users': user.role == 'admin'
        }
```

### **2.2 Service Testing Scenarios**

#### **Test 2.1: Candidate Management**
```python
# Test file: tests/services/test_candidate_service.py

async def test_create_candidate_with_auto_assignment():
    """Test that creating a candidate auto-assigns to creator"""
    # 1. Create candidate through service
    # 2. Verify candidate exists
    # 3. Verify auto-assignment exists
    # 4. Verify assignment is active
    pass

async def test_role_based_candidate_access():
    """Test junior recruiters only see assigned candidates"""
    # 1. Create candidates assigned to different users
    # 2. Test junior recruiter sees only assigned ones
    # 3. Test senior recruiter sees all
    # 4. Test admin sees all
    pass

async def test_candidate_reassignment():
    """Test candidate can be reassigned between users"""
    # 1. Create candidate assigned to User A
    # 2. Reassign to User B  
    # 3. Verify old assignment is deactivated
    # 4. Verify new assignment is active
    # 5. Verify assignment history is preserved
    pass
```

#### **Test 2.2: Resume Processing**
```python
# Test file: tests/services/test_resume_service.py

async def test_resume_upload_flow():
    """Test complete resume upload and processing"""
    # 1. Upload resume for candidate
    # 2. Verify resume record created
    # 3. Verify section extraction triggered
    # 4. Verify status updates correctly
    pass

async def test_resume_access_control():
    """Test users can only access resumes for assigned candidates"""
    # 1. Create resume for candidate assigned to User A
    # 2. Test User A can access resume
    # 3. Test User B (not assigned) cannot access
    # 4. Test admin can access all resumes
    pass
```

#### **Test 2.3: Review Workflow**
```python
# Test file: tests/services/test_review_service.py

async def test_review_request_authorization():
    """Test only authorized users can request reviews"""
    # 1. Create review request for assigned candidate
    # 2. Verify request succeeds
    # 3. Test unauthorized user request fails
    # 4. Verify proper error handling
    pass

async def test_ai_agent_integration():
    """Test AI agents are called correctly for reviews"""
    # 1. Create review request
    # 2. Verify correct prompts are loaded
    # 3. Verify agent_type specialization works
    # 4. Verify usage history is recorded
    pass
```

---

## **Phase 3: API Endpoint Integration Testing**

### **3.1 API Endpoints to Update**

#### **New Endpoints Required:**
```python
# app/api/v1/endpoints/candidates.py
@router.get("/candidates/", response_model=List[CandidateResponse])
async def get_candidates(current_user: User = Depends(get_current_user)):
    """Get candidates based on user role and assignments"""
    pass

@router.post("/candidates/", response_model=CandidateResponse)
async def create_candidate(candidate: CandidateCreate, current_user: User = Depends(get_current_user)):
    """Create new candidate with auto-assignment"""
    pass

@router.put("/candidates/{candidate_id}/assign")
async def assign_candidate(candidate_id: UUID, assignment: AssignmentCreate, current_user: User = Depends(get_current_user)):
    """Assign candidate to user (senior_recruiter/admin only)"""
    pass

# app/api/v1/endpoints/resumes.py (replaces files.py)
@router.post("/candidates/{candidate_id}/resumes/", response_model=ResumeResponse)
async def upload_resume(candidate_id: UUID, file: UploadFile, current_user: User = Depends(get_current_user)):
    """Upload resume for candidate"""
    pass

@router.get("/resumes/{resume_id}/", response_model=ResumeResponse) 
async def get_resume(resume_id: UUID, current_user: User = Depends(get_current_user)):
    """Get resume details with access control"""
    pass

# app/api/v1/endpoints/reviews.py (replaces analysis.py)
@router.post("/resumes/{resume_id}/reviews/", response_model=ReviewRequestResponse)
async def request_review(resume_id: UUID, review_params: ReviewCreate, current_user: User = Depends(get_current_user)):
    """Request AI review of resume"""
    pass
```

### **3.2 API Testing Scenarios**

#### **Test 3.1: Authentication & Authorization**
```python
# Test file: tests/api/test_auth_integration.py

async def test_role_based_endpoint_access():
    """Test endpoints respect role-based access"""
    # Test junior recruiter endpoints
    # Test senior recruiter endpoints  
    # Test admin endpoints
    # Verify proper 403 responses for unauthorized access
    pass

async def test_candidate_assignment_permissions():
    """Test assignment endpoints work correctly"""
    # Test senior can assign candidates
    # Test junior cannot assign candidates
    # Test assignment history is preserved
    pass
```

#### **Test 3.2: Data Flow Integration**
```python
# Test file: tests/api/test_workflow_integration.py

async def test_complete_recruitment_workflow():
    """Test end-to-end workflow through APIs"""
    # 1. POST /candidates/ (create candidate)
    # 2. POST /candidates/{id}/resumes/ (upload resume)
    # 3. POST /resumes/{id}/reviews/ (request review)
    # 4. GET /reviews/{id}/ (check results)
    # 5. Verify all database relationships are correct
    pass

async def test_concurrent_access():
    """Test multiple users accessing same resources"""
    # Test concurrent candidate access
    # Test concurrent resume uploads
    # Test race conditions in assignments
    pass
```

---

## **Phase 4: Database Transaction Testing**

### **4.1 Transaction Scenarios**

#### **Test 4.1: Complex Workflow Transactions**
```python
# Test file: tests/integration/test_transactions.py

async def test_candidate_creation_with_rollback():
    """Test transaction rollback on candidate creation failure"""
    # 1. Start transaction
    # 2. Create candidate
    # 3. Create assignment (force failure)
    # 4. Verify rollback removes candidate
    pass

async def test_reassignment_transaction():
    """Test candidate reassignment is atomic"""
    # 1. Start transaction  
    # 2. Deactivate old assignment
    # 3. Create new assignment
    # 4. Test partial failure scenarios
    # 5. Verify data consistency
    pass
```

#### **Test 4.2: Data Integrity Under Load**
```python
async def test_concurrent_assignments():
    """Test assignment integrity under concurrent access"""
    # Multiple users trying to assign same candidate
    # Verify no duplicate active assignments
    # Test constraint enforcement
    pass

async def test_bulk_operations():
    """Test bulk operations maintain integrity"""  
    # Bulk candidate creation
    # Bulk assignments
    # Verify performance and consistency
    pass
```

---

## **Phase 5: Performance & Load Testing**

### **5.1 Critical Query Performance**

#### **Queries to Test:**
```python
# Performance test scenarios
queries_to_test = [
    {
        "name": "User Dashboard",
        "query": "Get user's assigned candidates with resume counts",
        "expected_time": "< 50ms",
        "load_test": "100 concurrent users"
    },
    {
        "name": "Senior Recruiter View", 
        "query": "Get all candidates for senior recruiter",
        "expected_time": "< 100ms",
        "load_test": "50 concurrent requests"
    },
    {
        "name": "Resume Search",
        "query": "Search candidates and resumes by text",
        "expected_time": "< 200ms", 
        "load_test": "25 concurrent searches"
    }
]
```

### **5.2 Load Testing Checklist**
- [ ] **API Response Times**: All endpoints < 200ms under normal load
- [ ] **Database Connections**: Connection pool handles concurrent requests
- [ ] **Memory Usage**: No memory leaks during extended operation
- [ ] **Error Handling**: Graceful degradation under high load

---

## **Phase 6: Error Handling & Edge Cases**

### **6.1 Error Scenarios to Test**

#### **Business Logic Errors:**
```python
async def test_business_rule_enforcement():
    """Test business rules are enforced"""
    # Try to create duplicate assignments
    # Try unauthorized candidate access  
    # Try invalid role transitions
    # Verify proper error responses
    pass

async def test_data_validation():
    """Test input validation works correctly"""
    # Invalid email formats
    # Missing required fields
    # Field length violations
    # Verify error messages are helpful
    pass
```

#### **System Errors:**
```python
async def test_database_connection_failures():
    """Test handling of database connection issues"""
    # Simulate connection timeouts
    # Test retry logic
    # Verify graceful fallbacks
    pass

async def test_file_processing_errors():
    """Test resume upload error handling"""
    # Corrupted files
    # Unsupported formats
    # File size limits
    # Verify proper cleanup
    pass
```

---

## **Testing Execution Plan**

### **Week 1: Core Model & Service Integration**
- **Days 1-2**: Update SQLAlchemy models and test basic CRUD
- **Days 3-4**: Implement new services and test business logic  
- **Day 5**: Integration testing between services

### **Week 2: API & Performance Testing**
- **Days 1-2**: Update API endpoints and test individually
- **Days 3-4**: End-to-end workflow testing
- **Day 5**: Performance and load testing

### **Testing Environment Setup**

#### **Database Setup:**
```bash
# Use the migrated database for integration testing
# Database is already migrated and ready

# Verify migration status
PGPASSWORD=dev_password_123 psql -h localhost -U postgres -d ai_resume_review_dev -c "
SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1;
"
# Should show version 1.1.0
```

#### **Test Data:**
```python
# The migrated database already contains test data:
# - 217 users (10 admin, 18 senior, 189 junior)  
# - 11 candidates with assignments
# - 11 resumes with sections
# - 11 review requests
# - Complete workflow data for testing

# Additional test data can be created as needed
```

---

## **Success Criteria**

### **Phase Completion Criteria:**
- [ ] **All new models**: Working correctly with relationships
- [ ] **All services**: Implementing business logic correctly  
- [ ] **All API endpoints**: Respecting role-based access
- [ ] **Performance**: Meeting response time requirements
- [ ] **Error handling**: Graceful error responses
- [ ] **Data integrity**: No constraint violations under load
- [ ] **Workflow testing**: Complete end-to-end scenarios working

### **Production Readiness Checklist:**
- [ ] **Database migration**: ✅ Already completed
- [ ] **Backend integration**: ⏳ In progress
- [ ] **API documentation**: Updated for new endpoints
- [ ] **Frontend compatibility**: API contracts maintained
- [ ] **Performance benchmarks**: Met or exceeded
- [ ] **Security testing**: Role-based access validated
- [ ] **Load testing**: System stable under expected load

---

## **Risk Mitigation**

### **Rollback Plan:**
If integration testing reveals critical issues:

1. **Database rollback** available using backup tables:
   - `file_uploads_backup_v1_0`
   - `analysis_requests_backup_v1_0` 
   - `analysis_results_backup_v1_0`
   - `prompt_history_backup_v1_0`

2. **Code rollback** to previous version while database issues are resolved

3. **Gradual rollout** - Deploy to staging first, then production

### **Support During Integration:**
- **Database schema** is fully documented and validated
- **Migration scripts** are available for reference
- **Performance benchmarks** established for comparison
- **Business logic validation** completed for verification

---

## **Contact & Support**

**Database Migration Team**: Ready to assist with any schema-related questions  
**Migration Documentation**: Complete and available in `/database/docs/`  
**Performance Baselines**: Established and documented  
**Rollback Procedures**: Tested and ready if needed  

**The database is production-ready. Backend integration can proceed with confidence!** 🚀

---

*Backend Integration Test Plan v1.0*  
*Created: September 9, 2025*  
*Status: Ready for Backend Team Execution*