"""
Servislerde ortak hata sınıfları tanımlamak için kullanılır.

Matching, RAG veya orchestration servislerinde hata olduğunda aynı hata yapısını
kullanmak kodu daha okunabilir ve standart hale getirir.
"""

from typing import Any

from shared.enums import ErrorCode


class AppException(Exception):
    def __init__(
        self,
        message: str,
        error_code: ErrorCode | str,
        details: dict[str, Any] | None = None,
        status_code: int = 500,
    ):
        self.message = message
        self.error_code = error_code.value if isinstance(error_code, ErrorCode) else error_code
        self.details = details
        self.status_code = status_code
        super().__init__(message)


class ValidationException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details=details,
            status_code=400,
        )


class IntentException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INTENT_ERROR,
            details=details,
            status_code=500,
        )


class MatchingException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.MATCHING_ERROR,
            details=details,
            status_code=500,
        )


class RAGException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RAG_ERROR,
            details=details,
            status_code=500,
        )


class RetrievalException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.RETRIEVAL_ERROR,
            details=details,
            status_code=500,
        )


class LLMException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.LLM_ERROR,
            details=details,
            status_code=500,
        )


class NotFoundException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            details=details,
            status_code=404,
        )


class OutOfScopeException(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.OUT_OF_SCOPE,
            details=details,
            status_code=400,
        )