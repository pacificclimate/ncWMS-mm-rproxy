"""
This module provides translation of modelmeta unique_id to filepath,
with caching, and the option to reload (query the database anew) for a
unique_id that is already cached.
"""
import logging
from modelmeta import DataFile
from sqlalchemy.orm.exc import MultipleResultsFound


logger = logging.getLogger(__name__)


class Translation:
    def __init__(self, session, cache=False):
        """
        Constructor.

        :param session: SQLAlchemy session for modelmeta database
        :param cache: If False, don't cache. Otherwise use this object as
            the cache.
        """
        self.session = session
        self.cache = cache

    def get(self, unique_id):
        """Return the filepath corresponding to unique_id."""
        if self.cache is False:
            return self.load(unique_id)
        try:
            logger.debug(f"Cache hit: {unique_id}")
            return self.cache[unique_id]
        except KeyError:
            logger.debug(f"Cache miss: {unique_id}")
            return self.load(unique_id)

    def load(self, unique_id):
        """
        Look up filepath corresponding to unique_id in the database,
        cache the result if caching, and return the filepath.
        This is separate from `get` so that the client can force a new query
        on a unique_id already in the cache in case that value is outdated
        (which it is up to the client to determine).
        """
        logger.debug(f"Cache load: {unique_id}")
        try:
            filepath = (
                self.session.query(DataFile.filename)
                    .filter(DataFile.unique_id == unique_id)
                    .scalar()
            )
        except MultipleResultsFound:
            raise KeyError(
                f"Dataset id '{unique_id}' has multiple matches in metadata "
                f"database.This is an internal error and should be reported "
                f"to PCIC staff."
            )
        if filepath is None:
            raise KeyError(
                f"Dataset id '{unique_id}' not found in metadata database."
            )
        if self.cache is not False:
            self.cache[unique_id] = filepath
        return filepath

    def preload(self):
        """
        Preload the cache with a bunch o data. With this query, there is no
        particular order the results will come in (and no particular order
        that is likely to be useful), so it is a bit of shot in the dark
        unless the cache is very big. Which it likely will be.
        """
        if self.cache is False:
            logger.info(f"Cache preload: no caching")
            return
        query = self.session.query(DataFile.unique_id, DataFile.filename)
        if hasattr(self.cache, "maxsize"):
            query = query.limit(self.cache.maxsize)
        results = query.all()
        for unique_id, filepath in results:
            self.cache[unique_id] = filepath
        logger.info(f"Cache preload: {len(self.cache)} items")
