import json

from biketour_planner.utils.cache import json_cache, load_json_cache


def test_load_json_cache(tmp_path):
    cache_file = tmp_path / "cache.json"
    data = {"key": "value"}
    cache_file.write_text(json.dumps(data))

    assert load_json_cache(cache_file) == data


def test_load_json_cache_nonexistent(tmp_path):
    assert load_json_cache(tmp_path / "missing.json") == {}


def test_load_json_cache_invalid(tmp_path):
    cache_file = tmp_path / "invalid.json"
    cache_file.write_text("not json")
    assert load_json_cache(cache_file) == {}


def test_json_cache_internal(tmp_path):
    cache_file = tmp_path / "test_cache.json"

    @json_cache(cache_file)
    def my_func(x):
        return x * 2

    assert my_func(2) == 4
    assert cache_file.exists()

    # Check if it uses cache
    with open(cache_file) as f:
        content = json.load(f)
    assert "(2,)_{}" in content
    assert content["(2,)_{}"] == 4


def test_json_cache_external_dict(tmp_path):
    cache_file = tmp_path / "ext_cache.json"

    # We simulate the globals by putting things in the function's module or similar
    # But here we can just test if it works when we don't provide external names
    @json_cache(cache_file)
    def my_func(x):
        return x + 1

    assert my_func(5) == 6
    assert cache_file.exists()


def test_json_cache_exception_handling(tmp_path):
    # Test directory creation failure or similar
    # Using a path that is a directory where it expects a file might cause OSError
    bad_path = tmp_path / "dir"
    bad_path.mkdir()

    @json_cache(bad_path)
    def my_func(x):
        return x

    # Should not raise exception
    assert my_func(1) == 1
