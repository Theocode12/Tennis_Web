from functools import wraps
import threading

# Singleton Metaclass
class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()  # Thread safety for multi-threaded environments

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

