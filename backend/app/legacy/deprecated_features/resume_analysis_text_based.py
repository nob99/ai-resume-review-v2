"""
LEGACY: Old text-based resume analysis implementation.

This file contains the deprecated analyze_resume method that took raw text input
instead of referencing uploaded resumes. This was replaced in the two-feature
architecture refactoring.

DEPRECATED: September 2025
REPLACED BY: request_analysis method with resume_id parameter
"""

from typing import Optional
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class LegacyAnalysisMethod:
    """
    Legacy analyze_resume method that accepted raw text input.

    This method was part of the old API design where users had to copy/paste
    resume content into the analysis request. It has been replaced by the
    request_analysis method that references uploaded resumes by ID.
    """

    async def analyze_resume_DEPRECATED(
        self,
        request,  # Old AnalysisRequest with text field
        user_id: uuid.UUID
    ):
        """
        DEPRECATED: Main business logic interface for resume analysis.

        This method accepted raw text input which created a poor user experience
        requiring manual copy/paste. The new method references uploaded resumes.

        Args:
            request: Analysis request with text and industry (DEPRECATED SCHEMA)
            user_id: User requesting the analysis

        Returns:
            AnalysisResponse: Complete analysis response

        MIGRATION PATH:
        OLD: POST /analysis/analyze { "text": "...", "industry": "..." }
        NEW: POST /resumes/{id}/analyze { "industry": "..." }
        """

        try:
            # Step 1: Business logic - input validation
            await self._validate_analysis_request(request, user_id)

            # Step 2: Create analysis record
            file_upload_id = uuid.UUID(request.file_upload_id) if request.file_upload_id else None
            analysis = await self.repository.create_analysis(
                user_id=user_id,
                industry=request.industry,
                file_upload_id=file_upload_id
            )

            logger.info(f"Starting analysis {analysis.id} for user {user_id}, industry: {request.industry}")

            # Step 3: Update status to processing
            await self.repository.update_status(analysis.id, "PROCESSING")

            # Step 4: Business logic - preprocessing
            processed_text = self._preprocess_resume_text(request.text)  # ← RAW TEXT INPUT!

            # Step 5: Delegate to AI orchestrator (isolated module)
            ai_result = await self._call_ai_orchestrator(
                text=processed_text,
                industry=request.industry.value,
                analysis_id=str(analysis.id)
            )

            # Step 6: Business logic - post-processing and validation
            await self._validate_ai_result(ai_result)

            # Step 7: Parse and store results
            analysis_result = await self._parse_ai_result(ai_result, analysis.id)

            await self.repository.save_results(
                analysis_id=analysis.id,
                overall_score=analysis_result.overall_score,
                market_tier=analysis_result.market_tier,
                structure_scores=analysis_result.structure_scores.dict() if analysis_result.structure_scores else None,
                appeal_scores=analysis_result.appeal_scores.dict() if analysis_result.appeal_scores else None,
                confidence_metrics=analysis_result.confidence_metrics.dict() if analysis_result.confidence_metrics else None,
                structure_feedback=analysis_result.structure_feedback.specific_feedback if analysis_result.structure_feedback else None,
                appeal_feedback=analysis_result.appeal_feedback.specific_feedback if analysis_result.appeal_feedback else None,
                analysis_summary=analysis_result.analysis_summary,
                improvement_suggestions=", ".join(analysis_result.improvement_suggestions or []),
                ai_model_version=analysis_result.ai_model_version
            )

            # Step 8: Mark as completed
            await self.repository.update_status(analysis.id, "COMPLETED")

            # Step 9: Business logic - usage tracking
            self._track_analysis_usage(user_id, request.industry, analysis_result.overall_score)

            logger.info(
                f"Analysis {analysis.id} completed successfully "
                f"(score: {analysis_result.overall_score}, time: {analysis_result.processing_time_seconds:.2f}s)"
            )

            return {
                "analysis_id": str(analysis.id),
                "status": "COMPLETED",
                "result": analysis_result
            }

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            if 'analysis' in locals():
                await self.repository.update_status(analysis.id, "ERROR", str(e))
            raise Exception(f"Resume analysis failed: {str(e)}")


# Migration Notes:
"""
PROBLEMS WITH OLD METHOD:
1. Required users to copy/paste resume text manually
2. No connection to uploaded resume files
3. No candidate association or access control
4. Used deprecated file_upload_id instead of resume_id
5. Synchronous processing (blocking API calls)

NEW METHOD BENEFITS:
1. References uploaded resumes by ID (no copy/paste!)
2. Integrates with resume_upload service
3. Candidate-based access control
4. Async processing with polling
5. Analysis caching and optimization
6. Multiple analysis depths (quick/standard/deep)

API MIGRATION:
OLD: POST /api/v1/analysis/analyze
NEW: POST /api/v1/resumes/{resume_id}/analyze

SCHEMA MIGRATION:
OLD: { "text": "resume content...", "industry": "tech" }
NEW: { "industry": "tech", "analysis_depth": "standard" }
"""