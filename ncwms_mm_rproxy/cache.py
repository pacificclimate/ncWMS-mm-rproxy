from abc import ABC, abstractmethod
import os
from modelmeta import DataFile
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class CacheBase(ABC):
    """
    Abstract base class for a special kind of cache, where a cache miss is
    either
    - key not in cache
    - key in cache; associated value is invalid (e.g., out of date)
    """

    def __init__(self):
        self.cache = {}

    @abstractmethod
    def load_value(self, key):
        pass

    @abstractmethod
    def is_valid_value(self, value):
        pass

    def get(self, key):
        # TODO: It may be worth writing some more efficient code here
        if not (key in self.cache and self.is_valid_value(self.cache[key])):
            self.cache[key] = self.load_value(key)
        return self.cache[key]


class ModelmetaDatasetIdTranslationCache(CacheBase):
    """
    Cache for translations via modelmeta from unique_id to filepath.
    A filepath is valid if it exists in the filesystem.
    Typical reason it might not exist is that the file has moved and been
    reindexed. Worse reason is some kind of error in indexing.
    """

    def __init__(self, session):
        super().__init__()
        self.session = session

    def load_value(self, key):
        """
        Translate the unique_id to filepath via modelmeta.
        Check the filepath is valid.
        """
        try:
            filepath = (
                self.session.query(DataFile.filename)
                    .filter(DataFile.unique_id == key)
                    .scalar()
            )
        except MultipleResultsFound:
            raise MultipleResultsFound(
                f"Dataset id '{key}' has multiple matches in metadata database."
                f"This is an internal error and should be reported to PCIC "
                f"staff."
            )
        if filepath is None:
            raise NoResultFound(
                f"Dataset id '{key}' not found in metadata database."
            )
        # If this freshly retrieved filepath is not valid, we're in trouble.
        # This check is not strictly necessary, as the downstream user of this
        # value will also check it.
        # if not self.is_valid_value(filepath):
        #     raise ValueError(
        #         f"Filepath '{filepath}' corresponding to '{key}' "
        #         f"does not exist."
        #     )
        return filepath

    def is_valid_value(self, value):
        """Check that the filepath exists."""
        return os.path.exists(value)
