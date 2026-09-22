class OperationError(Exception):
    """Rejet définitif d'une opération de synchronisation : code + erreurs par champ."""

    def __init__(self, code: str, errors: dict | None = None):
        self.code = code
        self.errors = errors or {}
        super().__init__(code)
