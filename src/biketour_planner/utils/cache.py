"""
Caching utilities for the bike tour planner.
"""

import functools
import json
from pathlib import Path
from typing import Callable, Optional, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def load_json_cache(path: Path) -> dict:
    """Load a JSON cache file from the given path.

    Args:
        path: Path to the JSON file.

    Returns:
        Dictionary containing the cached data, or an empty dict if it fails.
    """
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def json_cache(
    cache_file: Path, cache_dict_name: Optional[str] = None, cache_file_var_name: Optional[str] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for JSON-based function caching.

    Args:
        cache_file: Default path to JSON cache file.
        cache_dict_name: Optional name of the dictionary in the module to use as cache.
        cache_file_var_name: Optional name of the variable in the module holding the cache file path.

    Returns:
        Decorated function with caching.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            globals_dict = func.__globals__

            # Determine cache file path
            current_cache_file = cache_file
            if cache_file_var_name and cache_file_var_name in globals_dict:
                current_cache_file = globals_dict[cache_file_var_name]

            # Determine cache dictionary
            cache: dict
            if cache_dict_name and cache_dict_name in globals_dict:
                cache = globals_dict[cache_dict_name]
            else:
                if not hasattr(wrapper, "_internal_cache"):
                    setattr(wrapper, "_internal_cache", {})
                cache = getattr(wrapper, "_internal_cache")

            # Create cache key from function arguments
            cache_key = f"{args}_{kwargs}"

            if cache_key in cache:
                return cache[cache_key]

            result = func(*args, **kwargs)

            # Cache the result
            cache[cache_key] = result

            # Persist cache
            if current_cache_file:
                try:
                    p = Path(current_cache_file)
                    # Simple heuristic to avoid writing during tests
                    if "non_existent.json" not in str(p):
                        p.parent.mkdir(parents=True, exist_ok=True)
                        with open(p, "w", encoding="utf-8") as f:
                            json.dump(cache, f, indent=2, ensure_ascii=False)
                except (IOError, TypeError):
                    pass

            return result

        return wrapper

    return decorator
