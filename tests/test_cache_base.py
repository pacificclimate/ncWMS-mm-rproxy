from ncwms_mm_rproxy.cache import CacheBase


class ATestCache(CacheBase):
    def __init__(self, source):
        super().__init__()
        self.orig_source = source
        self.reset()

    def reset(self):
        self.invalid = set()
        self.source = self.orig_source

    def load_value(self, key):
        return self.source[key]

    def set_valid(self, value):
        self.invalid.remove(value)

    def set_invalid(self, value):
        self.invalid.add(value)

    def is_valid_value(self, value):
        return value not in self.invalid


cache = ATestCache({f"key_{i}": f"value_{i}" for i in range(10)})


def test_simple_get():
    for i in range(10):
        assert cache.get(f"key_{i}") == f"value_{i}"


def test_value_invalidation():
    for i in range(10):
        key = f"key_{i}"
        value = f"value_{i}"
        assert cache.get(key) == value
        cache.set_invalid(value)
        new_value = f"new_value_{i}"
        cache.source[key] = new_value
        assert cache.get(key) == new_value
    cache.reset()
