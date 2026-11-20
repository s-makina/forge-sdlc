"""Capability vocabulary shared by models, profiles and agents.

Capabilities describe what a concrete model can do. They are deliberately a
closed vocabulary so that a capability requirement can never be satisfied by an
optionally-spelled "free text" flag: the model router relies on exact matches.
"""

from enum import StrEnum


class ModelCapability(StrEnum):
    """Declared capabilities of a model.

    ``CHAT`` is the baseline: every model used for agent work must support chat
    completions. The remaining capabilities are optional and are what routing
    policies and agent requirements key off.
    """

    CHAT = "chat"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    STREAMING = "streaming"
    VISION = "vision"


class AgentCapability(StrEnum):
    """Capabilities an agent declares about itself.

    These describe the kind of work the agent can perform. They are metadata that
    supports discovery and are distinct from model capabilities used for routing.
    """

    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    PLANNING = "planning"
    ARCHITECTURE = "architecture"
    CODE_ANALYSIS = "code_analysis"
    IMPLEMENTATION = "implementation"
    DEBUGGING = "debugging"
    UNIT_TESTING = "unit_testing"
    REFACTORING = "refactoring"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    SECURITY_ASSESSMENT = "security_assessment"
