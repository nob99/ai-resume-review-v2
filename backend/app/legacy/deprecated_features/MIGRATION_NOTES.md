# Migration Notes for Deprecated Features

## Resume Feature (Moved from app/features/resume)

**Replaced by**: Unified resume service in the refactoring plan
**Key Changes**:
- Resume creation now integrated with file upload (single endpoint)
- Candidate-centric design (resumes belong to candidates)
- Version management and duplicate detection
- Role-based access control

**Data Migration**: All existing resume data preserved in database

## Review Feature (Moved from app/features/review)

**Replaced by**: `app/features/resume_analysis`
**Key Changes**:
- On-demand analysis instead of automatic processing
- Polling-based results (better user experience)
- Industry-specific analysis prompts
- Cached results to avoid duplicate processing

**Data Migration**: Review data converted to new analysis format

## File Upload Integration

**Current Status**: `app/features/file_upload` still active
**Next Step**: Merge into unified resume service
**Timeline**: Next 2 weeks

## Testing

Legacy tests preserved for reference during migration:
- Resume service tests can guide new implementation
- Review service tests show expected behavior patterns
- Integration patterns can be adapted for new architecture

## APIs

Legacy API patterns can be found in these files for reference:
- Resume API patterns: `app/legacy/deprecated_features/resume/api.py`
- Review API patterns: `app/legacy/deprecated_features/review/api.py`

Remember: These are for reference only - do not import or use in new code!