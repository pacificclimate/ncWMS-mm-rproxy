import pytest
from unittest.mock import MagicMock
from ncwms_mm_rproxy import (
    get_dataset_ids,
    translate_dataset_id,
    translate_dataset_ids,
    reload_dataset_params,
)
from ncwms_mm_rproxy.translation import Translation


class TestHelpers:
    def test_get_dataset_ids_basic(self):
        # Dataset ID (before the slash)
        assert get_dataset_ids("abc/var1,def/var2") == ["abc", "def"]

    def test_translate_dataset_id_single(self):
        translations = MagicMock()
        translations.get.return_value = "/abc_translated"
        result = translate_dataset_id(translations, "abc/var", "prefix")
        # Should result in: prefix + translated path + variable
        assert result == "prefix/abc_translated/var"

    def test_translate_dataset_ids_multiple(self):
        # Translates multiple dataset IDs and joins their paths/variables
        translations = MagicMock()
        translations.get.side_effect = lambda x: f"/{x}_translated"
        result = translate_dataset_ids(translations, "abc/var1,def/var2", "dyn")
        expected = "dyn/abc_translated/var1,dyn/def_translated/var2"
        assert result == expected

    def test_reload_dataset_params_fetches_expected_ids(self):
        translations = MagicMock()
        translations.is_cached.return_value = True
        params = {"LAYER": "abc/var1,def/var2"}
        dataset_param_names = {"layer"}

        reload_dataset_params(translations, dataset_param_names, params)

        translations.fetch.assert_any_call("abc")
        translations.fetch.assert_any_call("def")
        assert translations.fetch.call_count == 2

    def test_preload_populates_cache(self):
        session = MagicMock()
        session.query.return_value.all.return_value = [
            ("a", "/data/a.nc"),
            ("b", "/data/b.nc"),
        ]
        cache = {}
        t = Translation(session, cache)
        t.preload()
        assert cache == {"a": "/data/a.nc", "b": "/data/b.nc"}
