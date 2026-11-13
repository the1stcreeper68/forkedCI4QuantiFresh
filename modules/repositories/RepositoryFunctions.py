from abc import ABC, abstractmethod


class RepositoryFunctions(ABC):
    """Interface: operations every single repository must support."""

    # [STATUS] NEW MODIFY
    #__ Require explicit household scope for cloud reads.
    @abstractmethod
    def load(self, household_id):
        pass

    # [STATUS] NEW MODIFY
    #__ Carry the draft and originally loaded version into the atomic save.
    @abstractmethod
    def save(self, document, expected_version):
        pass
