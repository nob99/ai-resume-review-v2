"""
Unit tests for TextProcessor (UPLOAD-003)

Tests text processing pipeline functionality including:
- Text cleaning and normalization
- Resume section detection
- Contact information extraction
- AI-ready data formatting
"""

import pytest
from unittest.mock import Mock, patch

from app.core.text_processor import (
    TextProcessor,
    ProcessedText,
    ResumeSection,
    SectionType,
    text_processor
)


class TestTextProcessor:
    """Test TextProcessor functionality."""
    
    @pytest.fixture
    def processor(self):
        """Create TextProcessor instance for testing."""
        return TextProcessor()
    
    def test_process_empty_text(self, processor):
        """Test processing empty text."""
        result = processor.process_text("")
        
        assert result.raw_text == ""
        assert result.cleaned_text == ""
        assert len(result.sections) == 0
        assert "error" in result.metadata
    
    def test_process_none_text(self, processor):
        """Test processing None text."""
        result = processor.process_text(None)
        
        assert result.raw_text == ""
        assert result.cleaned_text == ""
        assert "error" in result.metadata
    
    def test_clean_text_basic(self, processor):
        """Test basic text cleaning functionality."""
        raw_text = "  John   Doe  \n\n\n  Software Engineer  \n  "
        
        cleaned = processor._clean_text(raw_text)
        
        assert "John Doe" in cleaned
        assert "Software Engineer" in cleaned
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")
        # Should not have excessive whitespace
        assert "   " not in cleaned
    
    def test_clean_text_html_removal(self, processor):
        """Test HTML tag removal from text."""
        raw_text = "<p>John Doe</p><br><strong>Software Engineer</strong>"
        
        cleaned = processor._clean_text(raw_text)
        
        assert "John Doe" in cleaned
        assert "Software Engineer" in cleaned
        assert "<p>" not in cleaned
        assert "<br>" not in cleaned
        assert "<strong>" not in cleaned
    
    def test_clean_text_noise_patterns(self, processor):
        """Test removal of common resume noise patterns."""
        raw_text = """
        John Doe - Resume
        Page 1 of 2
        --- Page 1 ---
        Software Engineer
        CONFIDENTIAL
        """
        
        cleaned = processor._clean_text(raw_text)
        
        assert "John Doe" in cleaned
        assert "Software Engineer" in cleaned
        assert "Page 1 of 2" not in cleaned
        assert "--- Page 1 ---" not in cleaned
        assert "CONFIDENTIAL" not in cleaned
    
    def test_detect_contact_section(self, processor):
        """Test detection of contact information section."""
        text = """
        Contact Information
        John Doe
        john.doe@email.com
        (555) 123-4567
        
        Experience
        Software Engineer at TechCorp
        """
        
        sections = processor._detect_sections(text)
        
        contact_sections = [s for s in sections if s.section_type == SectionType.CONTACT]
        assert len(contact_sections) > 0
        
        contact_section = contact_sections[0]
        assert "john.doe@email.com" in contact_section.content
        assert "(555) 123-4567" in contact_section.content
    
    def test_detect_experience_section(self, processor):
        """Test detection of experience section."""
        text = """
        Work Experience
        
        Senior Software Engineer - TechCorp (2020-2023)
        • Developed web applications using Python and React
        • Led a team of 5 developers
        
        Software Engineer - StartupCo (2018-2020)
        • Built microservices architecture
        """
        
        sections = processor._detect_sections(text)
        
        experience_sections = [s for s in sections if s.section_type == SectionType.EXPERIENCE]
        assert len(experience_sections) > 0
        
        experience_section = experience_sections[0]
        assert "TechCorp" in experience_section.content
        assert "StartupCo" in experience_section.content
        assert "Python and React" in experience_section.content
    
    def test_detect_education_section(self, processor):
        """Test detection of education section."""
        text = """
        Education
        
        Master of Science in Computer Science
        University of Technology, 2018
        
        Bachelor of Science in Software Engineering
        State University, 2016
        """
        
        sections = processor._detect_sections(text)
        
        education_sections = [s for s in sections if s.section_type == SectionType.EDUCATION]
        assert len(education_sections) > 0
        
        education_section = education_sections[0]
        assert "Master of Science" in education_section.content
        assert "University of Technology" in education_section.content
    
    def test_detect_skills_section(self, processor):
        """Test detection of skills section."""
        text = """
        Technical Skills
        
        Programming Languages: Python, JavaScript, Java
        Frameworks: React, Django, Spring Boot
        Databases: PostgreSQL, MongoDB
        """
        
        sections = processor._detect_sections(text)
        
        skills_sections = [s for s in sections if s.section_type == SectionType.SKILLS]
        assert len(skills_sections) > 0
        
        skills_section = skills_sections[0]
        assert "Python" in skills_section.content
        assert "React" in skills_section.content
        assert "PostgreSQL" in skills_section.content
    
    def test_detect_multiple_sections(self, processor):
        """Test detection of multiple different sections."""
        text = """
        John Doe
        john.doe@email.com
        
        Professional Summary
        Experienced software engineer with 5+ years in web development
        
        Work Experience
        Senior Developer at TechCorp
        
        Education
        BS Computer Science
        
        Skills
        Python, React, PostgreSQL
        """
        
        sections = processor._detect_sections(text)
        
        section_types = {s.section_type for s in sections}
        
        # Should detect multiple section types
        assert len(section_types) >= 3
        assert SectionType.SUMMARY in section_types or SectionType.OTHER in section_types
        assert SectionType.EXPERIENCE in section_types
        assert SectionType.EDUCATION in section_types or SectionType.OTHER in section_types
        assert SectionType.SKILLS in section_types
    
    def test_identify_section_type_patterns(self, processor):
        """Test section type identification with various patterns."""
        test_cases = [
            ("Contact Information", SectionType.CONTACT),
            ("WORK EXPERIENCE", SectionType.EXPERIENCE),
            ("Professional Experience", SectionType.EXPERIENCE),
            ("Educational Background", SectionType.EDUCATION),
            ("Technical Skills", SectionType.SKILLS),
            ("Core Competencies", SectionType.SKILLS),
            ("Career Summary", SectionType.SUMMARY),
            ("Professional Objective", SectionType.SUMMARY),
            ("Certifications", SectionType.CERTIFICATIONS),
            ("Key Projects", SectionType.PROJECTS),
            ("Awards and Recognition", SectionType.ACHIEVEMENTS),
        ]
        
        for line, expected_type in test_cases:
            result = processor._identify_section_type(line.lower())
            assert result == expected_type, f"Failed for '{line}'"
    
    def test_identify_section_type_none(self, processor):
        """Test section type identification returning None for non-headers."""
        non_headers = [
            "This is just regular content text",
            "John Doe worked at TechCorp for 3 years developing applications",
            "A very long line of text that is unlikely to be a section header because it contains too much content",
        ]
        
        for line in non_headers:
            result = processor._identify_section_type(line)
            assert result is None
    
    def test_calculate_metadata_basic(self, processor):
        """Test basic metadata calculation."""
        raw_text = "Original text with some content"
        cleaned_text = "Cleaned text content"
        sections = [
            ResumeSection(SectionType.CONTACT, "Contact", "content", 0, 1, 0.8),
            ResumeSection(SectionType.EXPERIENCE, "Experience", "content", 2, 5, 0.9)
        ]
        
        metadata = processor._calculate_metadata(raw_text, cleaned_text, sections)
        
        assert metadata["sections_detected"] == 2
        assert "contact" in metadata["section_types"]
        assert "experience" in metadata["section_types"]
        assert metadata["text_metrics"]["raw_length"] == len(raw_text)
        assert metadata["text_metrics"]["cleaned_length"] == len(cleaned_text)
    
    def test_calculate_metadata_contact_extraction(self, processor):
        """Test contact information extraction in metadata."""
        text_with_contact = """
        John Doe
        john.doe@email.com
        jane.smith@company.com
        (555) 123-4567
        +1-555-987-6543
        """
        
        metadata = processor._calculate_metadata(text_with_contact, text_with_contact, [])
        
        contact_info = metadata["contact_info"]
        assert len(contact_info["emails_found"]) == 2
        assert "john.doe@email.com" in contact_info["emails_found"]
        assert "jane.smith@company.com" in contact_info["emails_found"]
        
        assert len(contact_info["phones_found"]) == 2
    
    def test_assess_text_quality_good(self, processor):
        """Test text quality assessment for good quality text."""
        good_text = """
        John Doe
        Software Engineer
        
        Professional Experience:
        Senior Developer at TechCorp (2020-2023)
        - Developed web applications using Python and React
        - Led cross-functional teams to deliver high-quality software solutions
        
        Education:
        Master of Science in Computer Science
        University of Technology, 2018
        
        Skills:
        Python, JavaScript, React, Django, PostgreSQL, AWS
        """
        
        quality = processor._assess_text_quality(good_text)
        assert quality == "good"
    
    def test_assess_text_quality_poor_short(self, processor):
        """Test text quality assessment for very short text."""
        poor_text = "John Doe"
        
        quality = processor._assess_text_quality(poor_text)
        assert quality == "poor"
    
    def test_assess_text_quality_poor_single_chars(self, processor):
        """Test text quality assessment for text with many single characters."""
        poor_text = "J\no\nh\nn\n \nD\no\ne\n"
        
        quality = processor._assess_text_quality(poor_text)
        assert quality == "poor"
    
    def test_assess_text_quality_fair(self, processor):
        """Test text quality assessment for fair quality text."""
        fair_text = "John Doe\nSoftware Engineer\nTechCorp\n123-456-7890\n!@#$%^&*()_+{}[]"
        
        quality = processor._assess_text_quality(fair_text)
        assert quality == "fair"
    
    def test_get_ai_ready_format(self, processor):
        """Test AI-ready data format generation."""
        processed_text = ProcessedText(
            raw_text="Raw resume text",
            cleaned_text="Cleaned resume text",
            sections=[
                ResumeSection(SectionType.CONTACT, "Contact", "john@email.com", 0, 1, 0.9),
                ResumeSection(SectionType.EXPERIENCE, "Experience", "Developer at TechCorp", 2, 5, 0.8)
            ],
            metadata={
                "contact_info": {
                    "emails_found": ["john@email.com"],
                    "phones_found": ["555-1234"]
                },
                "extraction_quality": "good"
            },
            word_count=10,
            line_count=5
        )
        
        ai_format = processor.get_ai_ready_format(processed_text)
        
        assert ai_format["text_content"] == "Cleaned resume text"
        assert ai_format["extraction_info"]["word_count"] == 10
        assert ai_format["extraction_info"]["line_count"] == 5
        assert ai_format["extraction_info"]["sections_detected"] == 2
        
        # Check sections structure
        sections = ai_format["structure"]["sections"]
        assert len(sections) == 2
        assert sections[0]["type"] == "contact"
        assert sections[1]["type"] == "experience"
    
    def test_process_text_complete_workflow(self, processor):
        """Test complete text processing workflow."""
        raw_text = """
        --- Page 1 ---
        
        John Doe
        Software Engineer
        john.doe@email.com
        (555) 123-4567
        
        Professional Experience
        
        Senior Software Engineer - TechCorp (2020-2023)
        • Developed web applications using Python and React
        • Led a team of 5 developers
        
        Education
        
        Master of Science in Computer Science
        University of Technology, 2018
        
        Technical Skills
        
        Python, JavaScript, React, Django, PostgreSQL
        
        page 2 of 2
        """
        
        result = processor.process_text(raw_text)
        
        # Check basic properties
        assert result.raw_text == raw_text
        assert len(result.cleaned_text) < len(raw_text)  # Should be cleaned
        assert result.word_count > 0
        assert result.line_count > 0
        
        # Check noise removal
        assert "--- Page 1 ---" not in result.cleaned_text
        assert "page 2 of 2" not in result.cleaned_text
        
        # Check sections detected
        assert len(result.sections) >= 3
        section_types = {s.section_type for s in result.sections}
        assert SectionType.EXPERIENCE in section_types
        assert SectionType.EDUCATION in section_types
        assert SectionType.SKILLS in section_types
        
        # Check metadata
        assert "processing_version" in result.metadata
        assert result.metadata["sections_detected"] > 0
        assert "contact_info" in result.metadata
        assert "john.doe@email.com" in result.metadata["contact_info"]["emails_found"]
    
    def test_get_section_by_type(self):
        """Test getting section by type."""
        sections = [
            ResumeSection(SectionType.CONTACT, "Contact", "content", 0, 1, 0.9),
            ResumeSection(SectionType.EXPERIENCE, "Experience", "content", 2, 5, 0.8),
            ResumeSection(SectionType.EXPERIENCE, "More Experience", "content", 6, 8, 0.7)
        ]
        
        processed_text = ProcessedText(
            raw_text="raw",
            cleaned_text="cleaned",
            sections=sections
        )
        
        contact_section = processed_text.get_section_by_type(SectionType.CONTACT)
        assert contact_section is not None
        assert contact_section.section_type == SectionType.CONTACT
        
        # Should return first match
        experience_section = processed_text.get_section_by_type(SectionType.EXPERIENCE)
        assert experience_section.title == "Experience"
        
        # Non-existent section
        skills_section = processed_text.get_section_by_type(SectionType.SKILLS)
        assert skills_section is None
    
    def test_get_sections_by_type(self):
        """Test getting all sections of a specific type."""
        sections = [
            ResumeSection(SectionType.CONTACT, "Contact", "content", 0, 1, 0.9),
            ResumeSection(SectionType.EXPERIENCE, "Experience", "content", 2, 5, 0.8),
            ResumeSection(SectionType.EXPERIENCE, "More Experience", "content", 6, 8, 0.7)
        ]
        
        processed_text = ProcessedText(
            raw_text="raw",
            cleaned_text="cleaned",
            sections=sections
        )
        
        experience_sections = processed_text.get_sections_by_type(SectionType.EXPERIENCE)
        assert len(experience_sections) == 2
        assert all(s.section_type == SectionType.EXPERIENCE for s in experience_sections)
        
        contact_sections = processed_text.get_sections_by_type(SectionType.CONTACT)
        assert len(contact_sections) == 1
        
        skills_sections = processed_text.get_sections_by_type(SectionType.SKILLS)
        assert len(skills_sections) == 0


class TestGlobalProcessorInstance:
    """Test the global text_processor instance."""
    
    def test_global_processor_exists(self):
        """Test that global processor instance exists."""
        assert text_processor is not None
        assert isinstance(text_processor, TextProcessor)
    
    def test_global_processor_section_patterns(self):
        """Test that global processor has section patterns configured."""
        assert len(text_processor._section_patterns) > 0
        assert SectionType.CONTACT in text_processor._section_patterns
        assert SectionType.EXPERIENCE in text_processor._section_patterns
        assert SectionType.EDUCATION in text_processor._section_patterns
        assert SectionType.SKILLS in text_processor._section_patterns


class TestResumeSection:
    """Test ResumeSection data class."""
    
    def test_resume_section_creation(self):
        """Test creating ResumeSection instance."""
        section = ResumeSection(
            section_type=SectionType.EXPERIENCE,
            title="Work Experience",
            content="Senior Developer at TechCorp",
            line_start=5,
            line_end=10,
            confidence=0.85
        )
        
        assert section.section_type == SectionType.EXPERIENCE
        assert section.title == "Work Experience"
        assert section.content == "Senior Developer at TechCorp"
        assert section.line_start == 5
        assert section.line_end == 10
        assert section.confidence == 0.85


class TestProcessedText:
    """Test ProcessedText data class."""
    
    def test_processed_text_creation(self):
        """Test creating ProcessedText instance."""
        processed_text = ProcessedText(
            raw_text="Raw text",
            cleaned_text="Cleaned text",
            word_count=2,
            line_count=1
        )
        
        assert processed_text.raw_text == "Raw text"
        assert processed_text.cleaned_text == "Cleaned text"
        assert processed_text.word_count == 2
        assert processed_text.line_count == 1
        assert len(processed_text.sections) == 0  # Default empty list
        assert len(processed_text.metadata) == 0  # Default empty dict


@pytest.mark.integration
class TestTextProcessorIntegration:
    """Integration tests for TextProcessor with real-like data."""
    
    def test_process_realistic_resume(self):
        """Test processing a realistic resume structure."""
        realistic_resume = """
        JOHN DOE
        Senior Software Engineer
        Email: john.doe@email.com | Phone: (555) 123-4567
        LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe
        
        PROFESSIONAL SUMMARY
        Experienced software engineer with 8+ years developing scalable web applications.
        Expertise in Python, JavaScript, and cloud technologies.
        
        PROFESSIONAL EXPERIENCE
        
        Senior Software Engineer | TechCorp Inc. | 2020 - Present
        • Led development of microservices architecture serving 1M+ users
        • Implemented CI/CD pipelines reducing deployment time by 60%
        • Mentored junior developers and conducted code reviews
        
        Software Engineer | StartupCo | 2018 - 2020
        • Built RESTful APIs using Python Flask and Django
        • Developed React frontend applications
        • Collaborated with product team on feature requirements
        
        EDUCATION
        
        Master of Science in Computer Science | University of Technology | 2018
        Relevant Coursework: Algorithms, Data Structures, Software Engineering
        
        Bachelor of Science in Software Engineering | State University | 2016
        Summa Cum Laude, GPA: 3.9/4.0
        
        TECHNICAL SKILLS
        
        Programming Languages: Python, JavaScript, TypeScript, Java
        Frameworks: React, Django, Flask, Node.js, Express
        Databases: PostgreSQL, MongoDB, Redis
        Cloud & DevOps: AWS, Docker, Kubernetes, Jenkins, Git
        
        PROJECTS
        
        E-commerce Platform (2023)
        • Full-stack web application with 10,000+ registered users
        • Technologies: React, Python, PostgreSQL, AWS
        
        CERTIFICATIONS
        
        AWS Certified Solutions Architect - Associate (2022)
        Certified Kubernetes Administrator (2021)
        """
        
        result = text_processor.process_text(realistic_resume)
        
        # Verify basic processing
        assert result.word_count > 100
        assert result.line_count > 20
        assert len(result.sections) >= 5
        
        # Verify section detection
        section_types = {s.section_type for s in result.sections}
        expected_sections = {
            SectionType.SUMMARY, SectionType.EXPERIENCE, SectionType.EDUCATION, 
            SectionType.SKILLS, SectionType.PROJECTS, SectionType.CERTIFICATIONS
        }
        
        # Should detect most expected sections (allowing for some flexibility)
        overlap = len(section_types.intersection(expected_sections))
        assert overlap >= 4
        
        # Verify contact extraction
        contact_info = result.metadata["contact_info"]
        assert "john.doe@email.com" in contact_info["emails_found"]
        assert len(contact_info["phones_found"]) >= 1
        
        # Verify text quality
        assert result.metadata["extraction_quality"] == "good"
        
        # Verify AI-ready format
        ai_format = text_processor.get_ai_ready_format(result)
        assert "structure" in ai_format
        assert "sections" in ai_format["structure"]
        assert len(ai_format["structure"]["sections"]) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])