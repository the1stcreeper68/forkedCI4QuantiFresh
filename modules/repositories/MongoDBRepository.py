# [STATUS] NEW MODIFY
#__ Scope cloud operations to one household and reject stale updates.
import os
from copy import deepcopy
from dotenv import load_dotenv
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from .RepositoryFunctions import RepositoryFunctions
from .HouseholdDocument import HouseholdDocument as Doc
from .StorageErrors import CloudUnavailable, HouseholdNotFound, SaveConflict


class MongoDBRepository(RepositoryFunctions):
    # [STATUS] NEW MODIFY
    #__ Inject a collection for tests; validate configuration for real connections.
    def __init__(self, database_name=None, collection=None):
        self.client = None
        if collection is not None:
            self.collection = collection
            return
        load_dotenv()
        uri = os.getenv("MONGODB_URI")
        name = database_name or os.getenv("MONGODB_DATABASE")
        if not uri or not name:
            raise CloudUnavailable("MONGODB_URI and MONGODB_DATABASE must be configured.")
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000,
                                  connectTimeoutMS=5000, socketTimeoutMS=10000, tz_aware=True)
        try:
            self.client.admin.command("ping")
        except ConnectionFailure as error:
            self.client.close()
            raise CloudUnavailable("MongoDB cannot be reached.") from error
        self.database = self.client[name]
        self.collection = self.database["households"]

    # [STATUS] NEW MODIFY
    #__ A confirmed missing ID must not fall back to a cached household.
    def load(self, household_id):
        household_id = Doc.normalize_id(household_id)
        try:
            document = self.collection.find_one({"_id": household_id})
        except ConnectionFailure as error:
            raise CloudUnavailable("MongoDB cannot be reached.") from error
        if document is None:
            raise HouseholdNotFound("Household ID was not found in MongoDB.")
        return Doc.from_cloud(document)

    # [STATUS] NEW ADDED
    #__ Retry an identical insertion safely after an uncertain network response.
    def create(self, document):
        Doc.size(document)
        try:
            self.collection.insert_one(Doc.to_cloud(document))
        except DuplicateKeyError:
            existing = self.load(document["_id"])
            if existing == document:
                return existing
            # [STATUS] NEW ADDED
            #__ An uncertain prior insertion may already have received another user's edits.
            if existing["created_at"] == document["created_at"]:
                raise SaveConflict("Previously created household has changed; review the draft before reloading.")
            raise
        except ConnectionFailure as error:
            raise CloudUnavailable("Creation could not be confirmed; retain the draft for retry.") from error
        return deepcopy(document)

    # [STATUS] NEW MODIFY
    #__ Save all arrays atomically using the originally loaded version, with no upsert.
    def save(self, document, expected_version):
        if document["version"] != expected_version:
            raise ValueError("Draft must retain its original cloud version.")
        Doc.size(document)
        try:
            updated = self.collection.find_one_and_update(
                {"_id": document["_id"], "version": expected_version},
                {"$set": Doc.editable(document), "$inc": {"version": 1},
                 "$currentDate": {"updated_at": True}},
                upsert=False, return_document=ReturnDocument.AFTER)
        except ConnectionFailure as error:
            raise CloudUnavailable("Save outcome is unknown; the local draft is preserved.") from error
        if updated is None:
            raise SaveConflict("This household changed or was removed. Review your draft before reloading.")
        return Doc.from_cloud(updated)

    # [STATUS] NEW ADDED
    #__ Release sockets explicitly for command-line migration and long-running callers.
    def close(self):
        if self.client is not None:
            self.client.close()

