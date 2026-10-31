from dataclasses import dataclass, field


@dataclass
class ClientContext:
    in_multi: bool = False
    queue: list[tuple[bytes, list[bytes]]] = field(default_factory=list)

    def reset_multi(self) -> None:
        self.in_multi = False
        self.queue.clear()