"""
Standart başarılı ve hatalı response üretmek için yardımcı fonksiyonlar içerir.

Neden kullanılır?
Tüm servislerde hata formatı aynı olsun diye kullanılır.
Frontend böylece her servisten gelen hatayı aynı yapıda okuyabilir.
"""

from __future__ import annotations

from typing import Any

from shared.exceptions import AppException
from shared.schemas import ErrorDetail


def build_error_detail(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> ErrorDetail:
    return ErrorDetail(
        code=code,
        message=message,
        details=details,
    )


def build_error_detail_from_exception(exc: AppException) -> ErrorDetail:
    return ErrorDetail(
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


def success_message(message: str = "İşlem başarılı.") -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "error": None,
    }


def error_message(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }