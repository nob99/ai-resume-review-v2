# Legacy Features Archive

This directory contains deprecated features that are being phased out during the backend refactoring.

## Migration Status

### ✅ Completed Migrations
- **auth**: Migrated to new JWT-based system with role-based access control
- **candidate**: New candidate-centric architecture implemented with full test coverage
- **resume_analysis**: New on-demand analysis service with polling-based results

### 🔄 In Progress
- **file_upload**: Being merged into unified resume service (functionality preserved)

### 📁 Archived Features (deprecated_features/)
- **resume**: Old resume service (replaced by new candidate-centric resume service)
- **review**: Old review system (replaced by resume_analysis with better structure)

## ⚠️ Important Notes

1. **DO NOT** reference these legacy features in new code
2. **Existing data** is preserved through database migrations
3. **APIs** are maintained for backward compatibility during transition
4. **Tests** for legacy features are preserved for reference

## Cleanup Schedule

- **Phase 1** (Current): Move to legacy archive ✅
- **Phase 2** (Next 2 weeks): Complete migration utilities
- **Phase 3** (Month end): Remove legacy archive after verification

## Migration Benefits

✅ **Eliminated** duplicate code between file_upload and resume services
✅ **Unified** user experience: Upload Resume → Request Analysis
✅ **Improved** performance with single source of truth for text storage
✅ **Enhanced** security with role-based candidate access control
✅ **Future-ready** architecture supports section-based enhancements

## Support

If you need to reference legacy implementations during migration:
- Check commit history: `git log --follow app/legacy/deprecated_features/`
- See refactoring plan: `backend/app/docs/refactoring_plan_20250912.md`
- Contact backend team for migration questions

---
*Generated during backend refactoring - September 2025*