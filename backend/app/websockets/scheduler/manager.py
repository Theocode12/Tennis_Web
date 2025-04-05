class SchedulerManager:
    def __init__(self):
        self.schedulers: dict[str, Scheduler] = {}

    def get_scheduler(self):
        pass

    def create_scheduler(self, game_id):
        pass

    def cleanup_scheduler(self, game_id):
        pass

    def cleanup(self):
        pass
