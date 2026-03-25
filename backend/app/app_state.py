import time

class AppState:
    def __init__(self):
        self.started_at = time.time()
        self.model_loading = True
        self.model_loaded = False
        self.ready = False
        self.model = None
        self.load_error = None
        self.model_name = None

state = AppState()