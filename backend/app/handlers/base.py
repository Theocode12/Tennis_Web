from backend.app.core.context import AppContext

class BaseHandler:
    def __init__(self, context: AppContext):
        self.context = context

    async def handle(self, sid: str, data: dict):
        raise NotImplementedError
