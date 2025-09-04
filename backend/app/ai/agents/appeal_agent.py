"""
Appeal Agent Implementation
===========================

The Appeal Agent performs industry-specific analysis of resume appeal and competitiveness.
It builds on the Structure Agent's results to provide targeted insights about how well
a resume positions the candidate within their target industry.

Key Responsibilities:
- Industry-specific achievement relevance analysis
- Skills alignment assessment for target industry
- Experience fit evaluation
- Competitive positioning analysis
- Market tier assessment
- Industry-specific recommendations

This agent uses context from the Structure Agent to provide comprehensive
industry-focused analysis while building on structural insights.
"""

import time
import re
import logging
from typing import Dict, Any, List, Optional, Literal

from .base_agent import BaseAgent
from app.ai.models.analysis_request import AnalysisState, AppealAnalysisResult, StructureAnalysisResult
from app.ai.integrations.base_llm import BaseLLM

logger = logging.getLogger(__name__)


class AppealAgent(BaseAgent):
    """
    Analyzes resume appeal and competitiveness for specific industries.
    
    This agent leverages context from the Structure Agent to provide targeted
    industry-specific analysis, focusing on how well the resume positions
    the candidate within their target market.
    """
    
    def __init__(self, llm_client: BaseLLM):
        """Initialize Appeal Agent with LLM client."""
        super().__init__(llm_client, "AppealAgent")
        
        # Score extraction patterns for parsing LLM output
        self.score_patterns = {
            "achievement_relevance_score": r"achievement[_\s]*(?:relevance[_\s]*)?score[:\s]*(\d+\.?\d*)",
            "skills_alignment_score": r"skills?[_\s]*alignment[_\s]*score[:\s]*(\d+\.?\d*)",
            "experience_fit_score": r"experience[_\s]*fit[_\s]*score[:\s]*(\d+\.?\d*)",
            "competitive_positioning_score": r"competitive[_\s]*(?:positioning[_\s]*)?score[:\s]*(\d+\.?\d*)"
        }
        
        # Industry-specific configurations
        self.industry_configs = self._initialize_industry_configs()
        
        # Feedback extraction keywords
        self.feedback_keywords = [
            "relevant_achievements", "missing_skills", "transferable_experience",
            "competitive_advantages", "improvement_areas", "industry_keywords"
        ]
        
        # Market tier keywords for assessment
        self.market_tier_keywords = {
            "entry": ["entry", "junior", "associate", "trainee", "intern", "beginner"],
            "mid": ["mid", "experienced", "specialist", "analyst", "coordinator"],
            "senior": ["senior", "lead", "principal", "manager", "supervisor"],
            "executive": ["executive", "director", "vp", "chief", "head", "president"]
        }
    
    def _initialize_industry_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize industry-specific configuration for analysis."""
        return {
            "tech_consulting": {
                "key_skills": [
                    "programming", "software development", "system architecture",
                    "cloud computing", "digital transformation", "agile", "scrum",
                    "data analysis", "machine learning", "cybersecurity"
                ],
                "important_achievements": [
                    "project delivery", "system implementation", "performance improvement",
                    "automation", "cost reduction", "team leadership", "client satisfaction"
                ],
                "market_indicators": {
                    "entry": ["bootcamp", "internship", "junior developer"],
                    "mid": ["3+ years", "team lead", "project management"],
                    "senior": ["architecture", "mentoring", "strategic planning"],
                    "executive": ["transformation", "business strategy", "p&l"]
                }
            },
            "system_integrator": {
                "key_skills": [
                    "systems integration", "enterprise software", "API development",
                    "database management", "middleware", "ERP", "CRM",
                    "business process", "technical documentation"
                ],
                "important_achievements": [
                    "integration projects", "system migration", "process automation",
                    "data integration", "workflow optimization", "stakeholder management"
                ],
                "market_indicators": {
                    "entry": ["technical support", "configuration"],
                    "mid": ["integration specialist", "solution design"],
                    "senior": ["enterprise architect", "program management"],
                    "executive": ["digital strategy", "business transformation"]
                }
            },
            "finance_banking": {
                "key_skills": [
                    "financial analysis", "risk management", "regulatory compliance",
                    "investment analysis", "portfolio management", "financial modeling",
                    "derivatives", "credit analysis", "capital markets"
                ],
                "important_achievements": [
                    "revenue generation", "risk mitigation", "cost optimization",
                    "regulatory compliance", "process improvement", "client acquisition"
                ],
                "market_indicators": {
                    "entry": ["analyst", "associate", "trainee"],
                    "mid": ["vice president", "relationship manager"],
                    "senior": ["director", "senior manager"],
                    "executive": ["managing director", "chief", "head of"]
                }
            },
            "healthcare_pharma": {
                "key_skills": [
                    "clinical research", "regulatory affairs", "drug development",
                    "medical devices", "healthcare management", "patient safety",
                    "quality assurance", "biostatistics", "pharmacovigilance"
                ],
                "important_achievements": [
                    "clinical trials", "regulatory approval", "patient outcomes",
                    "safety improvements", "cost reduction", "process optimization"
                ],
                "market_indicators": {
                    "entry": ["research assistant", "clinical coordinator"],
                    "mid": ["clinical researcher", "regulatory specialist"],
                    "senior": ["principal investigator", "medical director"],
                    "executive": ["chief medical officer", "vp clinical"]
                }
            },
            "manufacturing": {
                "key_skills": [
                    "lean manufacturing", "six sigma", "quality control",
                    "supply chain", "process optimization", "automation",
                    "safety management", "production planning", "continuous improvement"
                ],
                "important_achievements": [
                    "efficiency improvements", "cost reduction", "quality enhancement",
                    "safety record", "production optimization", "waste reduction"
                ],
                "market_indicators": {
                    "entry": ["operator", "technician", "coordinator"],
                    "mid": ["supervisor", "engineer", "specialist"],
                    "senior": ["manager", "senior engineer", "plant manager"],
                    "executive": ["director", "vp operations", "chief operations"]
                }
            },
            "general_business": {
                "key_skills": [
                    "business analysis", "project management", "strategic planning",
                    "operations management", "financial analysis", "marketing",
                    "sales", "customer service", "process improvement"
                ],
                "important_achievements": [
                    "revenue growth", "cost savings", "process improvements",
                    "team leadership", "project delivery", "customer satisfaction"
                ],
                "market_indicators": {
                    "entry": ["coordinator", "assistant", "associate"],
                    "mid": ["manager", "specialist", "lead"],
                    "senior": ["senior manager", "director"],
                    "executive": ["vp", "chief", "president"]
                }
            }
        }
    
    async def analyze(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Perform industry-specific appeal analysis with structure context.
        
        This is the main LangGraph node function that:
        1. Validates input state and structure context
        2. Calls LLM for industry-specific analysis
        3. Parses structured output with industry focus
        4. Returns state updates for workflow
        
        Args:
            state: Current workflow state including structure analysis results
            
        Returns:
            Dict containing appeal analysis results and state updates
        """
        start_time = time.time()
        
        try:
            # Validate input state
            self._validate_input_state(state)
            self._validate_structure_context(state)
            self._log_agent_start(state)
            
            # Prepare industry-specific analysis context
            analysis_context = self._prepare_analysis_context(state)
            
            # Get industry-specific analysis prompt
            analysis_prompt = self._build_industry_analysis_prompt(analysis_context)
            
            # Execute LLM analysis with industry focus
            logger.debug(f"Calling LLM for appeal analysis: {state['analysis_id']} (industry: {state['industry']})")
            llm_response = await self.llm.ainvoke(
                analysis_prompt,
                system_message=self._get_industry_system_message(state["industry"]),
                temperature=0.4,  # Slightly higher for creative industry insights
                max_tokens=3500
            )
            
            # Parse structured output with industry context
            structured_result = self._parse_appeal_output(
                llm_response.content,
                state["industry"],
                state.get("structure_analysis")
            )
            
            # Calculate industry-specific confidence
            confidence = self._calculate_appeal_confidence(
                structured_result,
                llm_response.content,
                state["industry"]
            )
            
            # Update result metadata
            processing_time_ms = self._get_processing_time_ms(start_time)
            structured_result.processing_time_ms = processing_time_ms
            structured_result.confidence_score = confidence
            structured_result.model_used = self.llm.model
            structured_result.target_industry = state["industry"]
            structured_result.structure_context_used = bool(state.get("structure_analysis"))
            
            self._log_agent_completion(state, confidence, processing_time_ms)
            
            # Return state updates for LangGraph workflow
            return {
                "appeal_analysis": structured_result,
                "appeal_confidence": confidence,
                "current_stage": "appeal_analysis",
                "appeal_errors": []
            }
            
        except Exception as e:
            logger.error(f"Appeal analysis failed for {state.get('analysis_id', 'unknown')}: {str(e)}")
            return self._handle_agent_error(e, state)
    
    def _validate_structure_context(self, state: AnalysisState) -> None:
        """
        Validate that structure analysis context is available.
        
        Args:
            state: Workflow state to validate
            
        Raises:
            ValueError: When structure context is missing or invalid
        """
        structure_analysis = state.get("structure_analysis")
        if not structure_analysis:
            logger.warning("No structure analysis available - appeal analysis will proceed without context")
            return
        
        # Validate structure analysis has basic required fields
        required_fields = ["format_score", "strengths", "recommendations"]
        missing_fields = [field for field in required_fields if not hasattr(structure_analysis, field)]
        
        if missing_fields:
            logger.warning(f"Structure analysis missing fields: {missing_fields}")
    
    def _prepare_analysis_context(self, state: AnalysisState) -> Dict[str, Any]:
        """
        Prepare context for industry-specific appeal analysis.
        
        Args:
            state: Current workflow state
            
        Returns:
            Dict containing comprehensive analysis context
        """
        resume_text = state["resume_text"]
        industry = state["industry"]
        structure_analysis = state.get("structure_analysis")
        
        # Get industry-specific configuration
        industry_config = self.industry_configs.get(industry, self.industry_configs["general_business"])
        
        # Extract structure context if available
        structure_context = {}
        if structure_analysis:
            structure_context = {
                "structure_strengths": structure_analysis.strengths[:3],  # Top 3 strengths
                "structure_recommendations": structure_analysis.recommendations[:2],  # Top 2 recommendations
                "sections_found": structure_analysis.total_sections_found,
                "overall_structure_quality": (
                    structure_analysis.format_score +
                    structure_analysis.section_organization_score +
                    structure_analysis.professional_tone_score +
                    structure_analysis.completeness_score
                ) / 4
            }
        
        return {
            "resume_text": resume_text,
            "industry": industry,
            "analysis_id": state["analysis_id"],
            "industry_config": industry_config,
            "structure_context": structure_context,
            "word_count": len(resume_text.split()),
            "has_structure_context": bool(structure_analysis)
        }
    
    def _build_industry_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build industry-specific analysis prompt for the LLM.
        
        Args:
            context: Analysis context prepared by _prepare_analysis_context
            
        Returns:
            str: Complete industry-specific analysis prompt
        """
        industry = context["industry"]
        industry_config = context["industry_config"]
        structure_context = context["structure_context"]
        
        structure_context_section = ""
        if context["has_structure_context"]:
            structure_context_section = f"""
STRUCTURE ANALYSIS CONTEXT:
The resume has been analyzed for structure with the following insights:
- Key Strengths: {', '.join(structure_context.get('structure_strengths', []))}
- Areas for Improvement: {', '.join(structure_context.get('structure_recommendations', []))}
- Overall Structure Quality: {structure_context.get('overall_structure_quality', 'Unknown'):.1f}/100
- Sections Identified: {structure_context.get('sections_found', 0)}

Use this context to inform your industry-specific analysis.
"""
        
        return f"""
Analyze the following resume for industry-specific appeal and competitiveness in the {industry.replace('_', ' ').title()} sector.

{structure_context_section}

RESUME TO ANALYZE:
{context['resume_text']}

ANALYSIS REQUIREMENTS FOR {industry.replace('_', ' ').upper()} INDUSTRY:

1. ACHIEVEMENT RELEVANCE ASSESSMENT (0-100 scale):
   - Relevance of accomplishments to {industry.replace('_', ' ')} industry
   - Impact and measurability of achievements
   - Industry-specific value demonstration
   - Competitive differentiation through achievements

2. SKILLS ALIGNMENT ASSESSMENT (0-100 scale):
   - Alignment with key {industry.replace('_', ' ')} skills: {', '.join(industry_config['key_skills'][:5])}
   - Technical and domain expertise demonstration
   - Skill progression and depth
   - Missing critical skills identification

3. EXPERIENCE FIT ASSESSMENT (0-100 scale):
   - Relevance of work experience to {industry.replace('_', ' ')}
   - Career progression appropriateness
   - Industry transition readiness (if applicable)
   - Experience depth and breadth

4. COMPETITIVE POSITIONING ASSESSMENT (0-100 scale):
   - Market competitiveness within {industry.replace('_', ' ')}
   - Unique value proposition strength
   - Differentiation from typical candidates
   - Overall market appeal

EXPECTED OUTPUT FORMAT:

SCORES:
- Achievement Relevance Score: [0-100]
- Skills Alignment Score: [0-100]
- Experience Fit Score: [0-100]
- Competitive Positioning Score: [0-100]

DETAILED INDUSTRY ANALYSIS:

Relevant Achievements:
- [List 3-5 most relevant achievements for {industry.replace('_', ' ')} industry]
- [Focus on quantifiable, impactful accomplishments]

Missing Skills:
- [List critical {industry.replace('_', ' ')} skills that are missing or underrepresented]
- [Prioritize by importance to industry success]

Transferable Experience:
- [Identify experience from other industries/roles that adds value]
- [Explain how it translates to {industry.replace('_', ' ')} context]

Industry Keywords:
- [List {industry.replace('_', ' ')}-specific terms and keywords found in resume]
- [Include both technical and business terms]

Competitive Advantages:
- [List unique selling points that differentiate this candidate]
- [Focus on {industry.replace('_', ' ')}-specific advantages]

Improvement Areas:
- [List 3-5 priority areas for enhancing {industry.replace('_', ' ')} appeal]
- [Provide specific, actionable recommendations]

Market Tier Assessment:
Based on experience level and achievements, classify as: Entry / Mid / Senior / Executive
Justification: [Brief explanation of tier assessment]

INDUSTRY FOCUS: {industry.replace('_', ' ').title()}
TARGET SKILLS: {', '.join(industry_config['key_skills'])}
KEY ACHIEVEMENTS: {', '.join(industry_config['important_achievements'])}

Provide thorough analysis focused specifically on {industry.replace('_', ' ')} industry requirements, market positioning, and competitive appeal.
Consider both current qualifications and potential for growth within this industry.
"""
    
    def _get_industry_system_message(self, industry: str) -> str:
        """
        Get industry-specific system message for the LLM.
        
        Args:
            industry: Target industry for analysis
            
        Returns:
            str: Industry-specific system message
        """
        industry_title = industry.replace('_', ' ').title()
        
        return f"""You are an expert {industry_title} industry analyst and recruitment specialist. Your role is to evaluate resumes specifically for their appeal and competitiveness within the {industry_title} sector.

You have deep knowledge of:
- {industry_title} industry requirements and trends
- Key skills and qualifications valued in {industry_title}
- Career progression patterns in {industry_title}
- Competitive landscape and market dynamics
- Industry-specific achievements that matter most

Your analysis focuses on:
- How well the candidate positions themselves for {industry_title} roles
- Competitive strengths and differentiators for this industry
- Alignment with {industry_title} employer expectations
- Market positioning and tier assessment
- Industry-specific improvement opportunities

Provide detailed, actionable insights that help candidates understand their appeal within the {industry_title} market and how to enhance their competitive positioning."""
    
    def _parse_appeal_output(
        self,
        raw_output: str,
        industry: str,
        structure_analysis: Optional[StructureAnalysisResult]
    ) -> AppealAnalysisResult:
        """
        Parse LLM output into structured AppealAnalysisResult.
        
        Args:
            raw_output: Raw LLM response text
            industry: Target industry for analysis
            structure_analysis: Structure analysis results for context
            
        Returns:
            AppealAnalysisResult: Parsed and validated result
        """
        try:
            # Extract scores using regex patterns
            scores = self._extract_scores_from_output(raw_output, self.score_patterns)
            
            # Extract feedback lists
            feedback = self._extract_industry_feedback(raw_output)
            
            # Determine market tier
            market_tier = self._assess_market_tier(raw_output, feedback)
            
            return AppealAnalysisResult(
                # Core industry scores
                achievement_relevance_score=scores.get("achievement_relevance_score", 75.0),
                skills_alignment_score=scores.get("skills_alignment_score", 75.0),
                experience_fit_score=scores.get("experience_fit_score", 75.0),
                competitive_positioning_score=scores.get("competitive_positioning_score", 75.0),
                
                # Industry-specific analysis
                relevant_achievements=feedback.get("relevant_achievements", []),
                missing_skills=feedback.get("missing_skills", []),
                transferable_experience=feedback.get("transferable_experience", []),
                industry_keywords=feedback.get("industry_keywords", []),
                
                # Competitive assessment
                market_tier=market_tier,
                competitive_advantages=feedback.get("competitive_advantages", []),
                improvement_areas=feedback.get("improvement_areas", []),
                
                # Context integration
                structure_context_used=bool(structure_analysis),
                target_industry=industry,
                
                # Metadata (will be set by calling function)
                confidence_score=0.0,
                processing_time_ms=0,
                model_used="",
                prompt_version="appeal_v1.0"
            )
            
        except Exception as e:
            logger.error(f"Error parsing appeal output: {str(e)}")
            return self._create_default_appeal_result(industry)
    
    def _extract_industry_feedback(self, raw_output: str) -> Dict[str, List[str]]:
        """
        Extract industry-specific feedback lists from LLM output.
        
        Args:
            raw_output: Raw LLM response
            
        Returns:
            Dict mapping feedback categories to extracted items
        """
        feedback = {
            "relevant_achievements": [],
            "missing_skills": [],
            "transferable_experience": [],
            "industry_keywords": [],
            "competitive_advantages": [],
            "improvement_areas": []
        }
        
        # Split output into lines for processing
        lines = raw_output.split('\n')
        current_category = None
        
        # Category detection patterns
        category_patterns = {
            "relevant_achievements": [r"relevant\s+achievements?", r"key\s+accomplishments?"],
            "missing_skills": [r"missing\s+skills?", r"skill\s+gaps?"],
            "transferable_experience": [r"transferable\s+experience", r"cross.*industry"],
            "industry_keywords": [r"industry\s+keywords?", r"sector.*terms?"],
            "competitive_advantages": [r"competitive\s+advantages?", r"unique.*selling"],
            "improvement_areas": [r"improvement\s+areas?", r"enhancement.*opportunities?"]
        }
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line indicates a new category
            line_lower = line.lower()
            for category, patterns in category_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_lower):
                        current_category = category
                        break
                if current_category == category:
                    break
            
            # Extract list items
            if current_category and re.match(r'^[-•*\d+\.]\s+', line):
                item = re.sub(r'^[-•*\d+\.]\s*', '', line).strip()
                if item and len(item) > 5:
                    feedback[current_category].append(item)
        
        return feedback
    
    def _assess_market_tier(self, raw_output: str, feedback: Dict[str, List[str]]) -> Literal["entry", "mid", "senior", "executive"]:
        """
        Assess market tier based on LLM output and extracted feedback.
        
        Args:
            raw_output: Raw LLM output
            feedback: Extracted feedback dictionary
            
        Returns:
            Market tier classification
        """
        # Look for explicit tier mention in output
        output_lower = raw_output.lower()
        for tier, keywords in self.market_tier_keywords.items():
            for keyword in keywords:
                if keyword in output_lower:
                    return tier
        
        # Fallback assessment based on achievements and experience indicators
        achievements = ' '.join(feedback.get("relevant_achievements", [])).lower()
        
        if any(word in achievements for word in ["executive", "director", "vp", "chief", "strategy"]):
            return "executive"
        elif any(word in achievements for word in ["senior", "lead", "manager", "architect"]):
            return "senior"
        elif any(word in achievements for word in ["specialist", "experienced", "analyst"]):
            return "mid"
        else:
            return "entry"
    
    def _calculate_appeal_confidence(
        self,
        result: AppealAnalysisResult,
        raw_output: str,
        industry: str
    ) -> float:
        """
        Calculate confidence specific to industry appeal analysis.
        
        Args:
            result: Parsed appeal analysis result
            raw_output: Raw LLM output
            industry: Target industry
            
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        confidence_factors = []
        
        # Factor 1: Score reasonableness
        scores = [
            result.achievement_relevance_score,
            result.skills_alignment_score,
            result.experience_fit_score,
            result.competitive_positioning_score
        ]
        valid_scores = sum(1 for score in scores if 0 <= score <= 100)
        score_confidence = valid_scores / len(scores)
        confidence_factors.append(("score_validity", score_confidence, 0.25))
        
        # Factor 2: Industry-specific feedback completeness
        industry_feedback_items = (
            len(result.relevant_achievements) +
            len(result.missing_skills) +
            len(result.competitive_advantages) +
            len(result.improvement_areas)
        )
        feedback_confidence = min(industry_feedback_items / 10, 1.0)
        confidence_factors.append(("industry_feedback", feedback_confidence, 0.25))
        
        # Factor 3: Industry keyword presence
        industry_config = self.industry_configs.get(industry, self.industry_configs["general_business"])
        expected_keywords = industry_config["key_skills"][:5]
        found_keywords = sum(1 for keyword in expected_keywords 
                           if any(keyword.lower() in raw_output.lower()))
        keyword_confidence = found_keywords / len(expected_keywords) if expected_keywords else 0.5
        confidence_factors.append(("industry_keywords", keyword_confidence, 0.2))
        
        # Factor 4: Market tier assessment reasonableness
        tier_confidence = 0.8 if result.market_tier in ["entry", "mid", "senior", "executive"] else 0.3
        confidence_factors.append(("market_tier", tier_confidence, 0.1))
        
        # Factor 5: Output structure and industry specificity
        structure_confidence = self._calculate_confidence(
            raw_output,
            ["achievement", "skills", "industry", "competitive", "market"],
            min_content_length=300
        )
        confidence_factors.append(("output_structure", structure_confidence, 0.2))
        
        # Calculate weighted confidence
        total_confidence = sum(factor[1] * factor[2] for factor in confidence_factors)
        
        # Ensure reasonable bounds
        return max(0.3, min(total_confidence, 1.0))
    
    def _create_default_appeal_result(self, industry: str) -> AppealAnalysisResult:
        """
        Create default result when parsing fails.
        
        Args:
            industry: Target industry
            
        Returns:
            AppealAnalysisResult: Default result with basic analysis
        """
        return AppealAnalysisResult(
            achievement_relevance_score=70.0,
            skills_alignment_score=70.0,
            experience_fit_score=70.0,
            competitive_positioning_score=70.0,
            
            relevant_achievements=["Unable to analyze achievements due to parsing error"],
            missing_skills=["Analysis incomplete - please retry"],
            transferable_experience=["Experience analysis was incomplete"],
            industry_keywords=["Keyword extraction failed"],
            
            market_tier="mid",
            competitive_advantages=["Analysis incomplete due to processing error"],
            improvement_areas=[
                "Please retry the analysis",
                "Ensure resume content is clear and well-formatted",
                "Contact support if issue persists"
            ],
            
            structure_context_used=False,
            target_industry=industry,
            
            confidence_score=0.3,
            processing_time_ms=0,
            model_used="",
            prompt_version="appeal_v1.0"
        )
    
    def _get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides."""
        return [
            "industry_specific_analysis",
            "achievement_relevance_assessment",
            "skills_alignment_evaluation",
            "competitive_positioning_analysis",
            "market_tier_assessment",
            "industry_recommendations",
            "cross_industry_experience_evaluation"
        ]
    
    def get_supported_industries(self) -> List[str]:
        """Get list of supported industries."""
        return list(self.industry_configs.keys())
    
    def get_industry_config(self, industry: str) -> Dict[str, Any]:
        """
        Get configuration for a specific industry.
        
        Args:
            industry: Industry name
            
        Returns:
            Dict containing industry configuration
        """
        return self.industry_configs.get(industry, self.industry_configs["general_business"]).copy()
    
    def validate_appeal_result(self, result: AppealAnalysisResult) -> bool:
        """
        Validate an appeal analysis result for completeness and correctness.
        
        Args:
            result: Appeal analysis result to validate
            
        Returns:
            bool: True if result is valid, False otherwise
        """
        try:
            # Check that all scores are within valid range
            scores = [
                result.achievement_relevance_score,
                result.skills_alignment_score,
                result.experience_fit_score,
                result.competitive_positioning_score
            ]
            
            if not all(0 <= score <= 100 for score in scores):
                return False
            
            # Check confidence is within valid range
            if not (0 <= result.confidence_score <= 1):
                return False
            
            # Check market tier is valid
            if result.market_tier not in ["entry", "mid", "senior", "executive"]:
                return False
            
            # Check required lists are present
            required_lists = [
                result.relevant_achievements,
                result.missing_skills,
                result.competitive_advantages,
                result.improvement_areas
            ]
            
            if not all(isinstance(lst, list) for lst in required_lists):
                return False
            
            # Check target industry is supported
            if result.target_industry not in self.get_supported_industries():
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating appeal result: {str(e)}")
            return False