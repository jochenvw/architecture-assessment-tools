"""Domain model: enums and dataclasses shared across the scanner.

These types define the stable vocabulary used by the database, collectors,
rule engine and reports. Keep them free of Azure access logic.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class ResourceClassification(str, enum.Enum):
    """Classification of a discovered cognitive-services style account."""

    FOUNDRY_CURRENT = "foundry-current"
    FOUNDRY_CLASSIC_HUB = "foundry-classic-hub"
    AZURE_OPENAI_ACCOUNT = "azure-openai-account"
    AI_SERVICES_ACCOUNT = "ai-services-account"
    UNKNOWN_COGNITIVE_ACCOUNT = "unknown-cognitive-account"


class TaskStatus(str, enum.Enum):
    """Lifecycle state of a single collector task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    BLOCKED_PERMISSION = "BLOCKED_PERMISSION"
    BLOCKED_NETWORK = "BLOCKED_NETWORK"
    UNSUPPORTED = "UNSUPPORTED"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    FAILED = "FAILED"


#: Task states considered terminal-success for progress accounting.
TASK_DONE_STATES = {TaskStatus.SUCCEEDED, TaskStatus.PARTIAL}
#: Task states that block work but must be preserved across resume.
TASK_BLOCKED_STATES = {TaskStatus.BLOCKED_PERMISSION, TaskStatus.BLOCKED_NETWORK}


class RuleResult(str, enum.Enum):
    """Outcome of a single rule evaluation against one resource."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class EffectiveResult(str, enum.Enum):
    """Result after applying exceptions to an underlying rule result."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"
    ACCEPTED_EXCEPTION = "ACCEPTED_EXCEPTION"


class EffortBand(str, enum.Enum):
    """Migration / upgrade effort sizing bands."""

    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    UNKNOWN = "UNKNOWN"


class Confidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceStatus(str, enum.Enum):
    """Collection status stored alongside each evidence record."""

    SUCCEEDED = "SUCCEEDED"
    PARTIAL = "PARTIAL"
    BLOCKED_PERMISSION = "BLOCKED_PERMISSION"
    BLOCKED_NETWORK = "BLOCKED_NETWORK"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Scope:
    """Describes the requested assessment scope."""

    kind: str  # tenant-wide | all-accessible | subscription | resource-group | resource | management-group
    values: tuple[str, ...] = ()

    def label(self) -> str:
        if self.values:
            return f"{self.kind}:{','.join(self.values)}"
        return self.kind


@dataclass
class ResourceRecord:
    """A discovered Azure resource in the inventory."""

    resource_id: str
    subscription_id: str
    resource_group: str
    name: str
    resource_type: str
    kind: Optional[str]
    sku: Optional[str]
    location: Optional[str]
    tags: dict[str, Any] = field(default_factory=dict)
    classification: Optional[str] = None
    properties: dict[str, Any] = field(default_factory=dict)
    source_query: Optional[str] = None


@dataclass
class Relationship:
    """A directed relationship between two resources with evidence provenance."""

    source_id: str
    target_id: str
    relationship_type: str
    evidence_type: str  # resource-id | connection | arm-property | apim-policy | private-endpoint | diagnostic | tag | naming
    confidence: str  # PROVEN | INFERRED
    collected_at: str


@dataclass
class Finding:
    """The result of evaluating one rule against one resource."""

    rule_id: str
    rule_version: str
    resource_id: str
    result: str
    severity: str
    expected: Any
    actual: Any
    explanation: str
    recommended_investigation: str
    collection_status: str
    foundry_resource_id: Optional[str] = None
    project_resource_id: Optional[str] = None
    evidence_ref: Optional[str] = None
    effective_result: Optional[str] = None
    exception_id: Optional[str] = None


@dataclass
class EffortEstimate:
    """A deterministic migration-effort estimate for one Foundry."""

    foundry_resource_id: str
    band: str
    confidence: str
    drivers: list[str] = field(default_factory=list)
    data_gb: float = 0.0
    unknown_dependencies: list[str] = field(default_factory=list)
