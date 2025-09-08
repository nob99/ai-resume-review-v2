"""
Prompt Versioning and A/B Testing Support
==========================================

This module provides versioning and A/B testing capabilities for AI prompts.
It enables controlled rollout of new prompt versions and comparison testing.

Key Features:
- Semantic versioning for prompts
- A/B testing framework
- Performance tracking per version
- Gradual rollout capabilities
- Rollback mechanisms
"""

import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.ai_agents.prompts.loader import PromptLoader, LoadedPrompt

logger = logging.getLogger(__name__)


class RolloutStage(Enum):
    """Stages of prompt rollout."""
    DEVELOPMENT = "development"
    CANARY = "canary"          # 5% traffic
    STAGED = "staged"          # 25% traffic  
    PRODUCTION = "production"  # 100% traffic
    ROLLBACK = "rollback"      # Rolled back to previous version


@dataclass
class PromptVersion:
    """Metadata for a specific prompt version."""
    
    name: str
    version: str
    description: str
    created_at: datetime
    stage: RolloutStage
    traffic_percentage: int = 0
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Set traffic percentage based on stage."""
        if self.traffic_percentage == 0:
            percentage_map = {
                RolloutStage.DEVELOPMENT: 0,
                RolloutStage.CANARY: 5,
                RolloutStage.STAGED: 25,
                RolloutStage.PRODUCTION: 100,
                RolloutStage.ROLLBACK: 0
            }
            self.traffic_percentage = percentage_map.get(self.stage, 0)


@dataclass 
class ABTestConfig:
    """Configuration for A/B testing between prompt versions."""
    
    test_name: str
    control_version: str
    treatment_version: str
    traffic_split: Dict[str, int]  # {'control': 50, 'treatment': 50}
    success_metrics: List[str]
    duration_days: int
    started_at: datetime
    status: str = "active"  # active, completed, paused


class PromptVersionManager:
    """
    Manages prompt versions and A/B testing.
    
    This class handles version selection, A/B testing logic, and performance tracking
    for different prompt versions.
    """
    
    def __init__(self, prompt_loader: Optional[PromptLoader] = None):
        """Initialize the version manager."""
        self.prompt_loader = prompt_loader or PromptLoader()
        self._version_registry: Dict[str, List[PromptVersion]] = {}
        self._ab_tests: Dict[str, ABTestConfig] = {}
        
        # Load version configurations
        self._load_version_configs()
    
    def get_prompt_for_request(
        self,
        prompt_name: str, 
        request_context: Dict[str, Any]
    ) -> Tuple[LoadedPrompt, str]:
        """
        Get the appropriate prompt version for a request based on A/B testing rules.
        
        Args:
            prompt_name: Name of the prompt to load
            request_context: Context about the request (user_id, session_id, etc.)
            
        Returns:
            Tuple of (LoadedPrompt, version_used)
        """
        # Check if there's an active A/B test for this prompt
        active_test = self._get_active_ab_test(prompt_name)
        
        if active_test:
            # Use A/B testing logic
            version = self._select_ab_test_version(active_test, request_context)
            logger.debug(f"A/B test selected version {version} for prompt {prompt_name}")
        else:
            # Use production version or staged rollout
            version = self._select_production_version(prompt_name, request_context)
            logger.debug(f"Production version {version} selected for prompt {prompt_name}")
        
        # Load the selected prompt version
        prompt = self.prompt_loader.load_prompt(prompt_name, version)
        return prompt, version
    
    def register_version(self, version_info: PromptVersion):
        """Register a new prompt version."""
        if version_info.name not in self._version_registry:
            self._version_registry[version_info.name] = []
        
        # Check if version already exists
        existing_versions = [v.version for v in self._version_registry[version_info.name]]
        if version_info.version in existing_versions:
            logger.warning(f"Version {version_info.version} already exists for {version_info.name}")
            return
        
        self._version_registry[version_info.name].append(version_info)
        logger.info(f"Registered version {version_info.version} for prompt {version_info.name}")
    
    def start_ab_test(self, test_config: ABTestConfig):
        """Start an A/B test between two prompt versions."""
        # Validate that both versions exist
        control_exists = self._version_exists(test_config.test_name, test_config.control_version)
        treatment_exists = self._version_exists(test_config.test_name, test_config.treatment_version)
        
        if not control_exists:
            raise ValueError(f"Control version {test_config.control_version} not found")
        if not treatment_exists:
            raise ValueError(f"Treatment version {test_config.treatment_version} not found")
        
        # Validate traffic split
        total_traffic = sum(test_config.traffic_split.values())
        if total_traffic != 100:
            raise ValueError(f"Traffic split must sum to 100, got {total_traffic}")
        
        self._ab_tests[test_config.test_name] = test_config
        logger.info(f"Started A/B test: {test_config.test_name}")
    
    def stop_ab_test(self, test_name: str):
        """Stop an active A/B test."""
        if test_name in self._ab_tests:
            self._ab_tests[test_name].status = "completed"
            logger.info(f"Stopped A/B test: {test_name}")
    
    def update_version_metrics(self, prompt_name: str, version: str, metrics: Dict[str, float]):
        """Update performance metrics for a prompt version."""
        versions = self._version_registry.get(prompt_name, [])
        for v in versions:
            if v.version == version:
                v.performance_metrics.update(metrics)
                logger.debug(f"Updated metrics for {prompt_name} v{version}")
                break
    
    def promote_version(self, prompt_name: str, version: str, target_stage: RolloutStage):
        """Promote a prompt version to a higher stage."""
        versions = self._version_registry.get(prompt_name, [])
        for v in versions:
            if v.version == version:
                old_stage = v.stage
                v.stage = target_stage
                # Update traffic percentage
                v.__post_init__()
                logger.info(f"Promoted {prompt_name} v{version} from {old_stage} to {target_stage}")
                break
    
    def rollback_version(self, prompt_name: str, to_version: Optional[str] = None):
        """Rollback to a previous version."""
        versions = self._version_registry.get(prompt_name, [])
        if not versions:
            raise ValueError(f"No versions found for prompt {prompt_name}")
        
        # Sort by version to find previous stable version
        stable_versions = [v for v in versions if v.stage == RolloutStage.PRODUCTION]
        stable_versions.sort(key=lambda x: x.version)
        
        if to_version:
            # Rollback to specific version
            target_version = next((v for v in versions if v.version == to_version), None)
            if not target_version:
                raise ValueError(f"Version {to_version} not found")
        else:
            # Rollback to previous stable version
            if len(stable_versions) < 2:
                raise ValueError("No previous stable version available for rollback")
            target_version = stable_versions[-2]  # Second to last
        
        # Mark current production version as rollback
        for v in versions:
            if v.stage == RolloutStage.PRODUCTION:
                v.stage = RolloutStage.ROLLBACK
        
        # Promote target version to production
        target_version.stage = RolloutStage.PRODUCTION
        target_version.__post_init__()
        
        logger.warning(f"Rolled back {prompt_name} to version {target_version.version}")
    
    def get_version_info(self, prompt_name: str) -> List[PromptVersion]:
        """Get all versions for a prompt."""
        return self._version_registry.get(prompt_name, [])
    
    def get_active_ab_tests(self) -> Dict[str, ABTestConfig]:
        """Get all active A/B tests."""
        return {name: config for name, config in self._ab_tests.items() 
                if config.status == "active"}
    
    def _get_active_ab_test(self, prompt_name: str) -> Optional[ABTestConfig]:
        """Get active A/B test for a prompt."""
        for test in self._ab_tests.values():
            if test.test_name == prompt_name and test.status == "active":
                return test
        return None
    
    def _select_ab_test_version(self, test_config: ABTestConfig, context: Dict[str, Any]) -> str:
        """Select version based on A/B test configuration."""
        # Use consistent hashing based on user_id or session_id
        user_id = context.get('user_id') or context.get('session_id', 'anonymous')
        
        # Create hash for consistent assignment
        hash_input = f"{test_config.test_name}_{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
        
        # Determine which bucket the user falls into
        control_percentage = test_config.traffic_split.get('control', 50)
        
        if hash_value < control_percentage:
            return test_config.control_version
        else:
            return test_config.treatment_version
    
    def _select_production_version(self, prompt_name: str, context: Dict[str, Any]) -> str:
        """Select production version based on staged rollout."""
        versions = self._version_registry.get(prompt_name, [])
        if not versions:
            return "1.0.0"  # Default version
        
        # Find production version
        production_versions = [v for v in versions if v.stage == RolloutStage.PRODUCTION]
        if production_versions:
            # Sort by version and return latest
            production_versions.sort(key=lambda x: x.version, reverse=True)
            return production_versions[0].version
        
        # Fallback to staged version if no production version
        staged_versions = [v for v in versions if v.stage == RolloutStage.STAGED]
        if staged_versions:
            # Use staged rollout logic
            user_id = context.get('user_id') or context.get('session_id', 'anonymous')
            hash_value = int(hashlib.md5(f"{prompt_name}_{user_id}".encode()).hexdigest(), 16) % 100
            
            staged_version = staged_versions[0]
            if hash_value < staged_version.traffic_percentage:
                return staged_version.version
        
        # Fallback to latest available version
        versions.sort(key=lambda x: x.version, reverse=True)
        return versions[0].version
    
    def _version_exists(self, prompt_name: str, version: str) -> bool:
        """Check if a prompt version exists."""
        versions = self._version_registry.get(prompt_name, [])
        return any(v.version == version for v in versions)
    
    def _load_version_configs(self):
        """Load version configurations from available prompts."""
        try:
            available_prompts = self.prompt_loader.get_available_prompts()
            
            for prompt_info in available_prompts:
                version_info = PromptVersion(
                    name=prompt_info['name'],
                    version=prompt_info['version'],
                    description=prompt_info['description'],
                    created_at=datetime.now(),
                    stage=RolloutStage.PRODUCTION,  # Default to production for existing prompts
                    tags=[]
                )
                self.register_version(version_info)
                
        except Exception as e:
            logger.error(f"Error loading version configurations: {str(e)}")


class PromptPerformanceTracker:
    """Tracks performance metrics for different prompt versions."""
    
    def __init__(self, version_manager: PromptVersionManager):
        self.version_manager = version_manager
        self._metrics_buffer: Dict[str, List[Dict]] = {}
    
    def record_usage(
        self,
        prompt_name: str,
        version: str,
        response_time_ms: float,
        success: bool,
        quality_score: Optional[float] = None,
        user_feedback: Optional[float] = None
    ):
        """Record usage metrics for a prompt version."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'response_time_ms': response_time_ms,
            'success': success,
            'quality_score': quality_score,
            'user_feedback': user_feedback
        }
        
        key = f"{prompt_name}:{version}"
        if key not in self._metrics_buffer:
            self._metrics_buffer[key] = []
        
        self._metrics_buffer[key].append(metrics)
        
        # Update aggregate metrics periodically
        if len(self._metrics_buffer[key]) % 10 == 0:  # Every 10 usages
            self._update_aggregate_metrics(prompt_name, version)
    
    def _update_aggregate_metrics(self, prompt_name: str, version: str):
        """Update aggregate metrics for a prompt version."""
        key = f"{prompt_name}:{version}"
        usage_data = self._metrics_buffer.get(key, [])
        
        if not usage_data:
            return
        
        # Calculate aggregates
        total_usages = len(usage_data)
        avg_response_time = sum(d['response_time_ms'] for d in usage_data) / total_usages
        success_rate = sum(1 for d in usage_data if d['success']) / total_usages
        
        quality_scores = [d['quality_score'] for d in usage_data if d['quality_score'] is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
        
        feedback_scores = [d['user_feedback'] for d in usage_data if d['user_feedback'] is not None]
        avg_feedback = sum(feedback_scores) / len(feedback_scores) if feedback_scores else None
        
        # Update version manager
        aggregate_metrics = {
            'total_usages': total_usages,
            'avg_response_time_ms': avg_response_time,
            'success_rate': success_rate
        }
        
        if avg_quality is not None:
            aggregate_metrics['avg_quality_score'] = avg_quality
        if avg_feedback is not None:
            aggregate_metrics['avg_user_feedback'] = avg_feedback
        
        self.version_manager.update_version_metrics(prompt_name, version, aggregate_metrics)


# Global version manager instance
_global_version_manager: Optional[PromptVersionManager] = None


def get_version_manager() -> PromptVersionManager:
    """Get the global version manager instance."""
    global _global_version_manager
    if _global_version_manager is None:
        _global_version_manager = PromptVersionManager()
    return _global_version_manager