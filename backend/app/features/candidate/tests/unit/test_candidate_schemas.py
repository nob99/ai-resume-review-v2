"""Unit tests for candidate schemas."""

import pytest
import uuid
from datetime import datetime
from pydantic import ValidationError

from app.features.candidate.schemas import (
    CandidateCreate,
    CandidateInfo,
    CandidateWithStats,
    CandidateListResponse,
    CandidateCreateResponse
)


class TestCandidateCreate:
    """Test candidate creation schema validation."""

    def test_valid_candidate_create_minimal(self):
        """Test minimal valid candidate creation."""
        data = {
            "first_name": "John",
            "last_name": "Doe"
        }
        candidate = CandidateCreate(**data)

        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
        assert candidate.email is None
        assert candidate.phone is None

    def test_valid_candidate_create_full(self):
        """Test full valid candidate creation."""
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "phone": "123-456-7890",
            "current_company": "Tech Corp",
            "current_position": "Software Engineer",
            "years_experience": 5
        }
        candidate = CandidateCreate(**data)

        assert candidate.first_name == "Jane"
        assert candidate.last_name == "Smith"
        assert candidate.email == "jane@example.com"
        assert candidate.phone == "123-456-7890"
        assert candidate.current_company == "Tech Corp"
        assert candidate.current_position == "Software Engineer"
        assert candidate.years_experience == 5

    def test_empty_first_name_validation(self):
        """Test validation fails for empty first name."""
        data = {
            "first_name": "",
            "last_name": "Doe"
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('first_name',) for error in errors)

    def test_empty_last_name_validation(self):
        """Test validation fails for empty last name."""
        data = {
            "first_name": "John",
            "last_name": ""
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('last_name',) for error in errors)

    def test_too_long_first_name(self):
        """Test validation fails for too long first name."""
        data = {
            "first_name": "A" * 101,  # Exceeds 100 char limit
            "last_name": "Doe"
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('first_name',) for error in errors)

    def test_invalid_email_format(self):
        """Test validation fails for invalid email."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid-email"
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('email',) for error in errors)

    def test_negative_years_experience(self):
        """Test validation fails for negative years of experience."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "years_experience": -1
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('years_experience',) for error in errors)

    def test_excessive_years_experience(self):
        """Test validation fails for excessive years of experience."""
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "years_experience": 51  # Exceeds 50 year limit
        }

        with pytest.raises(ValidationError) as exc_info:
            CandidateCreate(**data)

        errors = exc_info.value.errors()
        assert any(error['loc'] == ('years_experience',) for error in errors)


class TestCandidateInfo:
    """Test candidate info schema."""

    def test_candidate_info_creation(self):
        """Test candidate info schema creation."""
        candidate_id = uuid.uuid4()
        created_at = datetime.now()

        data = {
            "id": candidate_id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "123-456-7890",
            "current_company": "Tech Corp",
            "current_position": "Engineer",
            "years_experience": 5,
            "status": "active",
            "created_at": created_at
        }

        candidate = CandidateInfo(**data)

        assert candidate.id == candidate_id
        assert candidate.first_name == "John"
        assert candidate.last_name == "Doe"
        assert candidate.email == "john@example.com"
        assert candidate.status == "active"
        assert candidate.created_at == created_at


class TestCandidateWithStats:
    """Test candidate with stats schema."""

    def test_candidate_with_stats_default_values(self):
        """Test default values for stats."""
        candidate_id = uuid.uuid4()
        created_at = datetime.now()

        data = {
            "id": candidate_id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": None,
            "current_company": None,
            "current_position": None,
            "years_experience": None,
            "status": "active",
            "created_at": created_at
        }

        candidate = CandidateWithStats(**data)

        assert candidate.total_resumes == 0
        assert candidate.latest_resume_version == 0
        assert candidate.last_resume_upload is None

    def test_candidate_with_stats_custom_values(self):
        """Test custom values for stats."""
        candidate_id = uuid.uuid4()
        created_at = datetime.now()
        last_upload = datetime.now()

        data = {
            "id": candidate_id,
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "phone": "123-456-7890",
            "current_company": "Tech Corp",
            "current_position": "Senior Engineer",
            "years_experience": 8,
            "status": "active",
            "created_at": created_at,
            "total_resumes": 3,
            "latest_resume_version": 2,
            "last_resume_upload": last_upload
        }

        candidate = CandidateWithStats(**data)

        assert candidate.total_resumes == 3
        assert candidate.latest_resume_version == 2
        assert candidate.last_resume_upload == last_upload


class TestCandidateListResponse:
    """Test candidate list response schema."""

    def test_candidate_list_response_creation(self):
        """Test candidate list response creation."""
        candidate_id = uuid.uuid4()
        created_at = datetime.now()

        candidate_data = {
            "id": candidate_id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": None,
            "current_company": None,
            "current_position": None,
            "years_experience": None,
            "status": "active",
            "created_at": created_at
        }

        candidate = CandidateWithStats(**candidate_data)

        response_data = {
            "candidates": [candidate],
            "total_count": 1,
            "limit": 10,
            "offset": 0
        }

        response = CandidateListResponse(**response_data)

        assert len(response.candidates) == 1
        assert response.total_count == 1
        assert response.limit == 10
        assert response.offset == 0


class TestCandidateCreateResponse:
    """Test candidate create response schema."""

    def test_successful_create_response(self):
        """Test successful candidate creation response."""
        candidate_id = uuid.uuid4()
        created_at = datetime.now()

        candidate_data = {
            "id": candidate_id,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": None,
            "current_company": None,
            "current_position": None,
            "years_experience": None,
            "status": "active",
            "created_at": created_at
        }

        candidate = CandidateInfo(**candidate_data)

        response_data = {
            "success": True,
            "message": "Candidate created successfully",
            "candidate": candidate,
            "error": None
        }

        response = CandidateCreateResponse(**response_data)

        assert response.success is True
        assert response.message == "Candidate created successfully"
        assert response.candidate is not None
        assert response.error is None

    def test_failed_create_response(self):
        """Test failed candidate creation response."""
        response_data = {
            "success": False,
            "message": "Failed to create candidate",
            "candidate": None,
            "error": "Database connection failed"
        }

        response = CandidateCreateResponse(**response_data)

        assert response.success is False
        assert response.message == "Failed to create candidate"
        assert response.candidate is None
        assert response.error == "Database connection failed"