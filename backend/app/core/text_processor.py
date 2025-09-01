"""
Text Processing Pipeline for UPLOAD-003

Processes extracted text from resumes to create AI-ready structured output.
Handles cleaning, normalization, section detection, and formatting.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup
import unicodedata


class SectionType(str, Enum):
    """Resume section types for structured parsing."""
    CONTACT = "contact"
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    CERTIFICATIONS = "certifications"
    PROJECTS = "projects"
    ACHIEVEMENTS = "achievements"
    REFERENCES = "references"
    OTHER = "other"


@dataclass
class ResumeSection:
    """Represents a section of a resume."""
    section_type: SectionType
    title: str
    content: str
    line_start: int
    line_end: int
    confidence: float = 0.0


@dataclass
class ProcessedText:
    """Result of text processing with structured sections."""
    raw_text: str
    cleaned_text: str
    sections: List[ResumeSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    word_count: int = 0
    line_count: int = 0
    
    def get_section_by_type(self, section_type: SectionType) -> Optional[ResumeSection]:
        """Get first section of specified type."""
        for section in self.sections:
            if section.section_type == section_type:
                return section
        return None
    
    def get_sections_by_type(self, section_type: SectionType) -> List[ResumeSection]:
        """Get all sections of specified type."""
        return [s for s in self.sections if s.section_type == section_type]


class TextProcessor:
    """Main text processing pipeline for resume analysis."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Section detection patterns
        self._section_patterns = {
            SectionType.CONTACT: [
                r'contact\s+information',
                r'personal\s+information',
                r'contact\s+details',
                r'reach\s+me',
                r'get\s+in\s+touch'
            ],
            SectionType.SUMMARY: [
                r'professional\s+summary',
                r'career\s+summary',
                r'executive\s+summary',
                r'summary\s+of\s+qualifications',
                r'profile',
                r'objective',
                r'career\s+objective',
                r'professional\s+objective'
            ],
            SectionType.EXPERIENCE: [
                r'work\s+experience',
                r'professional\s+experience',
                r'employment\s+history',
                r'career\s+history',
                r'work\s+history',
                r'experience',
                r'employment'
            ],
            SectionType.EDUCATION: [
                r'education',
                r'educational\s+background',
                r'academic\s+background',
                r'qualifications',
                r'degrees'
            ],
            SectionType.SKILLS: [
                r'skills',
                r'technical\s+skills',
                r'core\s+competencies',
                r'competencies',
                r'expertise',
                r'technical\s+expertise',
                r'programming\s+skills',
                r'software\s+skills'
            ],
            SectionType.CERTIFICATIONS: [
                r'certifications',
                r'certificates',
                r'professional\s+certifications',
                r'licenses',
                r'credentials'
            ],
            SectionType.PROJECTS: [
                r'projects',
                r'key\s+projects',
                r'notable\s+projects',
                r'personal\s+projects',
                r'selected\s+projects'
            ],
            SectionType.ACHIEVEMENTS: [
                r'achievements',
                r'accomplishments',
                r'awards',
                r'honors',
                r'recognition'
            ]
        }
        
        # Email and phone patterns for contact extraction
        self._email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self._phone_pattern = re.compile(
            r'(?:\+?1[-.\s]?)?(?:\(?[0-9]{3}\)?[-.\s]?)?[0-9]{3}[-.\s]?[0-9]{4}'
        )
        
        # Common resume noise patterns to clean
        self._noise_patterns = [
            r'page\s+\d+\s+of\s+\d+',
            r'confidential',
            r'resume\s+of\s+',
            r'curriculum\s+vitae',
            r'\s+---\s+page\s+\d+\s+---\s+'
        ]
    
    def process_text(self, raw_text: str) -> ProcessedText:
        """
        Main processing pipeline for extracted text.
        
        Args:
            raw_text: Raw text extracted from resume file
            
        Returns:
            ProcessedText with cleaned text and detected sections
        """
        if not raw_text or not raw_text.strip():
            return ProcessedText(
                raw_text="",
                cleaned_text="",
                metadata={"error": "Empty input text"}
            )
        
        try:
            # Step 1: Clean and normalize text
            cleaned_text = self._clean_text(raw_text)
            
            # Step 2: Detect and extract sections
            sections = self._detect_sections(cleaned_text)
            
            # Step 3: Calculate metadata
            metadata = self._calculate_metadata(raw_text, cleaned_text, sections)
            
            return ProcessedText(
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                sections=sections,
                metadata=metadata,
                word_count=len(cleaned_text.split()),
                line_count=len(cleaned_text.splitlines())
            )
            
        except Exception as e:
            self.logger.error(f"Text processing failed: {str(e)}")
            return ProcessedText(
                raw_text=raw_text,
                cleaned_text=raw_text,
                metadata={"error": f"Processing failed: {str(e)}"}
            )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Remove HTML/XML tags if present
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove common resume noise patterns
        for pattern in self._noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Clean up line breaks (preserve paragraph structure)
        # Replace multiple line breaks with double line break
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _detect_sections(self, text: str) -> List[ResumeSection]:
        """Detect and extract resume sections from cleaned text."""
        sections = []
        lines = text.split('\n')
        
        current_section = None
        current_content = []
        
        for line_num, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Skip empty lines
            if not line_lower:
                if current_section and current_content:
                    current_content.append('')
                continue
            
            # Check if this line starts a new section
            detected_section = self._identify_section_type(line_lower)
            
            if detected_section:
                # Save previous section if it exists
                if current_section and current_content:
                    sections.append(ResumeSection(
                        section_type=current_section,
                        title=current_content[0] if current_content else '',
                        content='\n'.join(current_content[1:] if len(current_content) > 1 else current_content),
                        line_start=line_num - len(current_content),
                        line_end=line_num - 1,
                        confidence=0.8
                    ))
                
                # Start new section
                current_section = detected_section
                current_content = [line.strip()]
            else:
                # Add to current section
                if current_content:
                    current_content.append(line.strip())
                else:
                    # No section detected yet, create an "other" section
                    if not current_section:
                        current_section = SectionType.OTHER
                        current_content = [line.strip()]
        
        # Don't forget the last section
        if current_section and current_content:
            sections.append(ResumeSection(
                section_type=current_section,
                title=current_content[0] if current_content else '',
                content='\n'.join(current_content[1:] if len(current_content) > 1 else current_content),
                line_start=len(lines) - len(current_content),
                line_end=len(lines) - 1,
                confidence=0.7
            ))
        
        return sections
    
    def _identify_section_type(self, line: str) -> Optional[SectionType]:
        """Identify if a line represents a section header."""
        # Skip very long lines (unlikely to be section headers)
        if len(line) > 100:
            return None
        
        # Check against section patterns
        for section_type, patterns in self._section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return section_type
        
        # Check for section-like formatting (short line, possibly with special chars)
        if len(line.strip()) < 50 and any(char in line for char in [':', '-', '=', '_']):
            # This might be a section header, but we can't identify the type
            return SectionType.OTHER
        
        return None
    
    def _calculate_metadata(self, raw_text: str, cleaned_text: str, sections: List[ResumeSection]) -> Dict[str, Any]:
        """Calculate text processing metadata."""
        # Extract contact information
        emails = self._email_pattern.findall(cleaned_text)
        phones = self._phone_pattern.findall(cleaned_text)
        
        # Calculate section statistics
        section_stats = {}
        for section in sections:
            section_type = section.section_type.value
            if section_type not in section_stats:
                section_stats[section_type] = 0
            section_stats[section_type] += 1
        
        # Text quality metrics
        avg_words_per_line = len(cleaned_text.split()) / max(len(cleaned_text.splitlines()), 1)
        
        return {
            "processing_version": "1.0",
            "extraction_quality": self._assess_text_quality(cleaned_text),
            "sections_detected": len(sections),
            "section_types": list(section_stats.keys()),
            "section_statistics": section_stats,
            "contact_info": {
                "emails_found": emails,
                "phones_found": phones,
                "has_contact_section": any(s.section_type == SectionType.CONTACT for s in sections)
            },
            "text_metrics": {
                "raw_length": len(raw_text),
                "cleaned_length": len(cleaned_text),
                "compression_ratio": len(cleaned_text) / max(len(raw_text), 1),
                "avg_words_per_line": round(avg_words_per_line, 2)
            }
        }
    
    def _assess_text_quality(self, text: str) -> str:
        """Assess the quality of extracted text."""
        if not text or len(text.strip()) < 100:
            return "poor"
        
        # Check for common extraction issues
        lines = text.split('\n')
        
        # Too many single-character lines (OCR issues)
        single_char_lines = sum(1 for line in lines if len(line.strip()) == 1)
        if single_char_lines > len(lines) * 0.3:
            return "poor"
        
        # Check for reasonable word/line ratio
        words = text.split()
        if len(words) < len(lines) * 0.5:  # Less than 0.5 words per line on average
            return "poor"
        
        # Check for reasonable character distribution
        alpha_chars = sum(1 for char in text if char.isalpha())
        if alpha_chars < len(text) * 0.5:  # Less than 50% alphabetic characters
            return "fair"
        
        return "good"
    
    def get_ai_ready_format(self, processed_text: ProcessedText) -> Dict[str, Any]:
        """Convert processed text to AI-ready structured format."""
        ai_format = {
            "text_content": processed_text.cleaned_text,
            "metadata": processed_text.metadata,
            "structure": {
                "sections": []
            },
            "extraction_info": {
                "word_count": processed_text.word_count,
                "line_count": processed_text.line_count,
                "sections_detected": len(processed_text.sections)
            }
        }
        
        # Add structured sections for AI processing
        for section in processed_text.sections:
            ai_format["structure"]["sections"].append({
                "type": section.section_type.value,
                "title": section.title,
                "content": section.content,
                "position": {
                    "line_start": section.line_start,
                    "line_end": section.line_end
                },
                "confidence": section.confidence
            })
        
        return ai_format


# Global processor instance
text_processor = TextProcessor()