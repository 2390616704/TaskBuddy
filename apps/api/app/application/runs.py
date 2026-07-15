from dataclasses import dataclass

from app.domain.provider import CancelSignal


@dataclass(slots=True)
class RunLease:
    cancel: CancelSignal
    message_id: str | None = None


class RunRegistry:
    def __init__(self) -> None:
        self._runs: dict[str, RunLease] = {}

    def reserve(self, conversation_id: str) -> RunLease | None:
        if conversation_id in self._runs:
            return None
        lease = RunLease(cancel=CancelSignal())
        self._runs[conversation_id] = lease
        return lease

    def release(self, conversation_id: str, lease: RunLease) -> None:
        if self._runs.get(conversation_id) is lease:
            self._runs.pop(conversation_id)

    def cancel(self, conversation_id: str, message_id: str) -> bool:
        lease = self._runs.get(conversation_id)
        if lease is None or lease.message_id != message_id:
            return False
        lease.cancel.cancel()
        return True
