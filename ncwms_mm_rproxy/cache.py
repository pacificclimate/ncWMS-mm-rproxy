from modelmeta import DataFile
from sqlalchemy.orm.exc import MultipleResultsFound
from cachetools import LFUCache


class TranslationCache(LFUCache):
    """
    A cache for the translations retrieved from modelmeta.
    Cache key is modelmeta unique_id.
    Cached value is corresponding modelmeta filepath.

    By defining method `__missing__`, we automagically retrieve any missing
    translation and put it into the cache.

    Method `preload` preloads the cache with a large number of translations.
    This speeds up the initial phase in which the cache becomes filled by usage.
    """

    def __init__(self, session, maxsize):
        """
        Constructor

        :param session: SQLAlchemy database session for modelmeta database.
            Used for retrieving translations.
        :param maxsize: Maximum size of cache.
        """
        super().__init__(maxsize)
        self.session = session

    def __missing__(self, key):
        """Retrieve the value (filepath) for a key (unique_id) from the
        database and put it in the cache."""
        print(f"cache miss for {key}")
        try:
            filepath = (
                self.session.query(DataFile.filename)
                    .filter(DataFile.unique_id == key)
                    .scalar()
            )
        except MultipleResultsFound:
            raise KeyError(
                f"Dataset id '{key}' has multiple matches in metadata database."
                f"This is an internal error and should be reported to PCIC "
                f"staff."
            )
        if filepath is None:
            raise KeyError(
                f"Dataset id '{key}' not found in metadata database."
            )
        self[key] = filepath
        return filepath

    def reload(self, key):
        """Force a cached value to be reloaded. This is useful when it turns
        out a translation is no longer valid (e.g., file has moved)."""
        return self.__missing__(key)

    def preload(self):
        """
        Preload the cache with a bunch o data. With this query, there is no
        particular order the results will come in (and no particular order
        that is likely to be useful), so it is a bit of shot in the dark
        unless the cache is very big. Which it likely will be.
        """
        results = (
            self.session
                .query(DataFile.unique_id, DataFile.filename)
                .limit(self.maxsize)
                .all()
        )
        for unique_id, filepath in results:
            self[unique_id] = filepath
