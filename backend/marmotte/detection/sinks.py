"""Where alerts go: a JSON lines stream for now (lot 3 adds the send queue)."""

import json
from typing import Protocol
from typing import TextIO

from marmotte.detection.types import AlertEvent


class AlertSink(Protocol):
    """Receive the alerts decided by the detection chain."""

    def emit(self, event: AlertEvent) -> None:
        """Handle one alert."""
        ...


class JsonLinesSink:
    """Write each alert as one line of JSON."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    def emit(self, event: AlertEvent) -> None:
        record = {
            "id": str(event.id),
            "kind": event.kind.value,
            "at": event.at.isoformat(),
            "offset_s": round(event.offset_s, 4),
            "via_scream_net": event.via_scream_net,
        }
        self._stream.write(json.dumps(record) + "\n")
        self._stream.flush()
