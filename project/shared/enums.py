from enum import Enum


class IntentType(str, Enum):
    GREETING = "greeting"
    GENERAL_INFO = "general_info"
    INCENTIVE_RECOMMENDATION = "incentive_recommendation"
    RAG_QUESTION = "rag_question"
    ELIGIBILITY_QUESTION = "eligibility_question"
    PROFILE_UPDATE = "profile_update"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


class TargetService(str, Enum):
    ORCHESTRATION = "orchestration_service"
    MATCHING = "matching_service"
    RAG = "rag_service"
    NONE = "none"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTENT_ERROR = "INTENT_ERROR"
    MATCHING_ERROR = "MATCHING_ERROR"
    RAG_ERROR = "RAG_ERROR"
    LLM_ERROR = "LLM_ERROR"
    RETRIEVAL_ERROR = "RETRIEVAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class Language(str, Enum):
    TR = "tr"
    EN = "en"
