"""Offline stand-in for the Anthropic client, for tests of translator callers."""

from __future__ import annotations

import json
from types import SimpleNamespace

PREFIX = "번역-"
MARKER = "keys:\n"


def reply(payload, **usage):
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    u = {"input_tokens": 1000, "output_tokens": 100}
    u.update(usage)
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], usage=SimpleNamespace(**u))


class EchoClient:
    """Answers every request by prefixing each requested field with PREFIX.

    ``usage`` overrides the reply's token counts (``output_tokens=50000`` costs
    about $0.50 on the static model). ``calls`` records each request. ``fail_when`` is a predicate on the requested
    fields; when it returns True the reply is not JSON, which the translator
    retries once and then raises TranslationError for.
    """

    def __init__(self, fail_when=None, **usage):
        self.calls: list[dict] = []
        self.fail_when = fail_when
        self.usage = usage
        self.messages = self

    def requested_fields(self, call: dict) -> dict[str, str]:
        content = call["messages"][0]["content"]
        return json.loads(content[content.index(MARKER) + len(MARKER):])

    def create(self, **kwargs):
        self.calls.append(kwargs)
        fields = self.requested_fields(kwargs)
        if self.fail_when and self.fail_when(fields):
            return reply("not json", **self.usage)
        return reply({k: PREFIX + v for k, v in fields.items()}, **self.usage)

    @property
    def requested(self) -> list[dict[str, str]]:
        return [self.requested_fields(c) for c in self.calls]
