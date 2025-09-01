UPLOAD-003 Sample Files Instructions

This directory contains sample resume files for testing text extraction functionality.

Files included:
- sample_resume_text.txt: Text version of sample resume
- sample_resume_simple.pdf: Simple PDF resume (if reportlab available)
- sample_resume_complex.pdf: Complex multi-page PDF (if reportlab available)  
- sample_resume.docx: DOCX resume with tables (if python-docx available)

To create additional test files:
1. Install dependencies: pip install reportlab python-docx
2. Run this script again
3. Or manually create PDF/DOCX files using the text content as reference

Test Scenarios:
- Basic text extraction from different file formats
- Section detection and classification
- Contact information extraction
- Multi-page document handling
- Table and formatting preservation
- Error handling with corrupted files

For corrupted file testing:
- Create files with invalid headers or truncated content
- Test with password-protected documents
- Test with scanned PDFs (image-based content)
