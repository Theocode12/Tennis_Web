from __future__ import annotations

import threading
from typing import Any, ClassVar, TypeVar, cast

# Generic type variable to represent the instance being created
T = TypeVar("T")


class SingletonMeta(type):
    # Shared across all classes using this metaclass
    _instances: ClassVar[dict[type, Any]] = {}

    # Lock to make it thread-safe
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __call__(cls: type[T], *args: Any, **kwargs: Any) -> T:
        """
        Controls the instantiation of classes using this metaclass.
        Ensures only one instance of each such class exists.
        """
        # Lock ensures that only one thread can create the instance at a time
        with SingletonMeta._lock:
            # If no instance exists yet for this class, create one
            if cls not in SingletonMeta._instances:
                # Call the original constructor using the base type
                instance = type.__call__(cls, *args, **kwargs)
                # Store the created instance in the _instances cache
                SingletonMeta._instances[cls] = instance

        # Return the stored (singleton) instance, casting for type checker
        return cast(T, SingletonMeta._instances[cls])
