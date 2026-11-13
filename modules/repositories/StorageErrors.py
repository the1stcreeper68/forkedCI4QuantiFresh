# [STATUS] NEW ADDED
#__ Distinguish stale edits, absent households, and connectivity failures.
class SaveConflict(RuntimeError):
    pass


class LocalConflict(SaveConflict):
    pass


class HouseholdNotFound(RuntimeError):
    pass


class CloudUnavailable(RuntimeError):
    pass
