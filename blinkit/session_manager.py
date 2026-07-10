class SessionManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SessionManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.valid = True
        self._initialized = True

    def invalidate(self):
        self.valid = False

    def restore(self):
        self.valid = True

    def is_valid(self):
        return self.valid


# Export a global singleton instance
session_manager = SessionManager()
