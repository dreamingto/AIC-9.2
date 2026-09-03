from enum import StrEnum


class EvidenceState(StrEnum):
    OBSERVED = "Observed"
    DOCUMENTED = "Documented"
    INFERRED = "Inferred"
    VERIFIED = "Verified"


class VerificationState(StrEnum):
    PENDING = "pending"
    WORTH_COMPARING = "worth_comparing"
    REJECTED = "rejected"
    DISPUTED = "disputed"
    VERIFIED = "verified"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RelationType(StrEnum):
    DRIVES = "drives"
    TRANSMITS = "transmits"
    CONNECTS = "connects"
    ACTS_ON = "acts_on"
    OUTPUTS = "outputs"
    LOCATED_IN = "located_in"


class SearchType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    REGION = "region"
