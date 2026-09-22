import logging

logger = logging.getLogger("cacaotrack.app_version")


class AppVersionLoggingMiddleware:
    """P2 (architecture) : journalise X-App-Version pour repérer les téléphones sur
    une ancienne version. Aucune donnée personnelle dans ce journal."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        version = request.headers.get("X-App-Version")
        if version:
            logger.info(
                "request app_version=%s method=%s path=%s", version, request.method, request.path
            )
        return self.get_response(request)
