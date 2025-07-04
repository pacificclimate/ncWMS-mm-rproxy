import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm.exc import MultipleResultsFound
from ncwms_mm_rproxy.translation import Translation


class TestTranslation:
    def test_is_cached(self):
        session = MagicMock()
        assert Translation(session, {}).is_cached() is True
        assert Translation(session, None).is_cached() is False

    def test_preload_basic(self):
        session = MagicMock()
        session.query.return_value.all.return_value = [("a", "/a.nc")]
        cache = {}
        t = Translation(session, cache)
        t.preload()
        # Cache should now contain the mapping
        assert cache == {"a": "/a.nc"}

    def test_cache_hit(self):
        session = MagicMock()
        cache = {"abc123": "/data/file1.nc"}
        t = Translation(session, cache)
        # T.get will return self.cache[unique_id] without querying DB
        assert t.get("abc123") == "/data/file1.nc"
        session.query.assert_not_called()

    def test_db_hit_on_cache_miss(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.scalar.return_value = (
            "/data/file2.nc"
        )
        cache = {}
        t = Translation(session, cache)
        assert "def456" not in cache
        result = t.get("def456")
        assert result == "/data/file2.nc"
        # Now cache should have the result
        assert cache["def456"] == "/data/file2.nc"

    def test_keyerror_on_missing_dataset(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.scalar.return_value = None
        t = Translation(session, {})
        with pytest.raises(KeyError, match="not found"):
            t.get("missing123")

    def test_keyerror_on_multiple_matches(self):
        #  Multiple rows match unique_id
        session = MagicMock()
        session.query.return_value.filter.return_value.scalar.side_effect = (
            MultipleResultsFound
        )
        t = Translation(session, {})
        with pytest.raises(KeyError, match="multiple matches"):
            t.get("dupe001")
