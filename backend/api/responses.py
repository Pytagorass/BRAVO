from django.http import JsonResponse


def success_response(data=None, code="OK", status_code=200):
    return JsonResponse(
        {
            "success": True,
            "data": data if data is not None else {},
        },
        status=status_code,
    )


def error_response(message, code="ERRO_INTERNO", status_code=400, details=None):
    error_payload = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details

    return JsonResponse(
        {
            "success": False,
            "error": error_payload,
        },
        status=status_code,
    )
