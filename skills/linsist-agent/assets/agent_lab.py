#!/usr/bin/env python3
"""Offline fixtures and student entry points. Core exercises are intentionally empty."""

import argparse
from copy import deepcopy
import json


class FakeLLM:
    """Return a finite, deterministic script; never call a provider."""

    def __init__(self, replies):
        self.replies = deepcopy(list(replies))
        self.calls = 0

    def next(self):
        if self.calls >= len(self.replies):
            raise RuntimeError("Fake LLM script exhausted")
        reply = deepcopy(self.replies[self.calls])
        self.calls += 1
        return reply


def run_loop(llm, max_steps):
    """A01: consume continue/final messages within a step limit."""
    raise NotImplementedError("A01: implement after the concept check")


def dispatch(call, tools):
    """A02: validate and dispatch an allowlisted integer add call."""
    raise NotImplementedError("A02")


def append_observation(messages, call_id, result):
    """A03: associate an observation with its existing tool call."""
    raise NotImplementedError("A03")


def transition(state, event):
    """A04: apply one legal state transition."""
    raise NotImplementedError("A04")


def trim_context(messages, max_chars):
    """A05: preserve system and latest user input within a character budget."""
    raise NotImplementedError("A05")


def memory_budget(age_days, base):
    """A06: calculate a synthetic time-band character budget."""
    raise NotImplementedError("A06")


def confirm(proposal, approved, current_user):
    """A07: enforce ownership, confirmation and in-memory repeat protection."""
    raise NotImplementedError("A07")


def ngram_coverage(reference, candidate, n=4):
    """A08: calculate candidate n-gram coverage, not semantic entailment."""
    raise NotImplementedError("A08")


def rewrite_once(draft, rewrite):
    """A09: allow at most one eligible rewrite with tools disabled."""
    raise NotImplementedError("A09")


def handle_rpc(request, tools):
    """A10: an educational JSON-RPC subset, not a complete MCP server."""
    raise NotImplementedError("A10")


def redact_event(event):
    """A11: project an event onto allowlisted trace metadata."""
    raise NotImplementedError("A11")


def evaluate(cases):
    """A12: calculate a deterministic offline task pass rate."""
    raise NotImplementedError("A12")


def remaining_budget(deadline_ms, now_ms, min_required_ms=0):
    """A13: decide whether remaining time can admit the next operation."""
    raise NotImplementedError("A13")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", required=True,
                        help="Verify only the Fake LLM fixture, not student exercises")
    parser.parse_args()
    llm = FakeLLM([{"type": "continue"}, {"type": "final", "answer": "fixture ready"}])
    replies = [llm.next(), llm.next()]
    print(json.dumps({"status": "fixture_ready", "calls": llm.calls,
                      "replies": replies, "exercises_passed": False}))


if __name__ == "__main__":
    main()
