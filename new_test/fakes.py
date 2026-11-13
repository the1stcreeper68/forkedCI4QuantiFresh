# [STATUS] NEW ADDED
#__ A locked in-memory collection exercises the real repository without cloud access.
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from pymongo.errors import DuplicateKeyError, ConnectionFailure


class MemoryCollection:
    # [STATUS] NEW ADDED
    #__ Record operations and allow deterministic network failures in tests.
    def __init__(self):
        self.documents = {}
        self.lock = Lock()
        self.offline = False
        self.reads = []
        self.writes = []

    # [STATUS] NEW ADDED
    #__ Simulate connectivity independently from absent records.
    def check(self):
        if self.offline:
            raise ConnectionFailure("test offline")

    # [STATUS] NEW ADDED
    #__ Match MongoDB's unique household primary key.
    def insert_one(self, document):
        self.check()
        with self.lock:
            if document["_id"] in self.documents:
                raise DuplicateKeyError("duplicate")
            self.documents[document["_id"]] = deepcopy(document)

    # [STATUS] NEW ADDED
    #__ Assert that ordinary reads never request an unfiltered collection.
    def find_one(self, query):
        self.check()
        assert set(query) == {"_id"}
        self.reads.append(query)
        with self.lock:
            return deepcopy(self.documents.get(query["_id"]))

    # [STATUS] NEW ADDED
    #__ Model the atomic version predicate and post-update return value.
    def find_one_and_update(self, query, update, upsert, return_document):
        self.check()
        assert upsert is False
        with self.lock:
            self.writes.append(deepcopy((query, update)))
            current = self.documents.get(query["_id"])
            if current is None or current["version"] != query["version"]:
                return None
            current.update(deepcopy(update["$set"]))
            current["version"] += update["$inc"]["version"]
            current["updated_at"] = datetime.now(timezone.utc)
            return deepcopy(current)
