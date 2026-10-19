#!/usr/bin/env python3
"""Run only the selected student's exercise contract; no solutions or provider calls."""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from agent_lab import FakeLLM


def check_loop(m, c):
    llm = FakeLLM([{"type": "continue"}, {"type": "final", "answer": "done"}, {"type": "continue"}])
    c.assertEqual(m.run_loop(llm, 3), {"status": "completed", "answer": "done", "steps": 2})
    c.assertEqual(llm.calls, 2, "No call after final")
    llm = FakeLLM([{"type": "continue"}] * 4)
    c.assertEqual(m.run_loop(llm, 2), {"status": "budget_exhausted", "answer": None, "steps": 2})
    c.assertEqual(llm.calls, 2)
    with c.assertRaises(ValueError):
        m.run_loop(llm, 0)
    with c.assertRaises(ValueError):
        m.run_loop(FakeLLM([{"type": "unexpected"}]), 1)
    with c.assertRaises(RuntimeError):
        m.run_loop(FakeLLM([]), 1)


def check_dispatch(m, c):
    calls = []
    def add(a, b):
        calls.append((a, b))
        return a + b
    tools = {"add": add}
    c.assertEqual(m.dispatch({"name": "add", "arguments": {"a": 2, "b": 3}}, tools), {"result": 5})
    c.assertEqual(m.dispatch({"name": "shell", "arguments": {}}, tools), {"error": "unknown_tool"})
    for args in ({"a": True, "b": 2}, {"a": "2", "b": 3}, {"a": 1}, {"a": 1, "b": 2, "extra": 3}):
        c.assertEqual(m.dispatch({"name": "add", "arguments": args}, tools), {"error": "invalid_arguments"})
    c.assertEqual(calls, [(2, 3)], "Invalid calls must have zero tool effects")


def check_observation(m, c):
    messages = [{"role": "assistant", "tool_call": {"id": "c1", "name": "add"}}]
    before = deepcopy(messages)
    c.assertEqual(m.append_observation(messages, "c1", 5),
                  messages + [{"role": "tool", "tool_call_id": "c1", "content": "5"}])
    c.assertEqual(messages, before)
    with c.assertRaises(ValueError):
        m.append_observation(messages, "missing", 5)


def check_transition(m, c):
    transitions = [("IDLE", "start", "RUNNING"), ("RUNNING", "propose", "WAITING_CONFIRMATION"),
                   ("WAITING_CONFIRMATION", "approve", "RUNNING"), ("RUNNING", "final", "COMPLETED"),
                   ("RUNNING", "timeout", "FAILED")]
    for state, event, expected in transitions:
        c.assertEqual(m.transition(state, event), expected)
    for state, event in [("COMPLETED", "start"), ("FAILED", "start"), ("IDLE", "approve")]:
        with c.assertRaises(ValueError):
            m.transition(state, event)


def check_context(m, c):
    messages = [{"role": "system", "content": "rule"}, {"role": "user", "content": "old"},
                {"role": "assistant", "content": "ok"}, {"role": "user", "content": "now"}]
    before = deepcopy(messages)
    c.assertEqual(m.trim_context(messages, 9), [messages[0], messages[2], messages[3]])
    c.assertEqual(m.trim_context(messages, 7), [messages[0], messages[3]])
    c.assertEqual(m.trim_context(messages, 20), messages)
    c.assertEqual(messages, before)
    with c.assertRaises(ValueError):
        m.trim_context(messages, 6)
    with c.assertRaises(ValueError):
        m.trim_context([], 10)


def check_memory(m, c):
    for age, expected in [(0, 100), (29, 100), (30, 75), (179, 75), (180, 50), (900, 50), (None, 40)]:
        c.assertEqual(m.memory_budget(age, 100), expected)
    c.assertEqual(m.memory_budget(None, 20), 20)
    c.assertEqual(m.memory_budget(180, 101), 50)
    c.assertEqual(m.memory_budget(0, 0), 0)
    with c.assertRaises(ValueError):
        m.memory_budget(-1, 100)
    with c.assertRaises(ValueError):
        m.memory_budget(1, -1)


def check_confirmation(m, c):
    proposal = {"id": "p1", "owner": "u1", "status": "PROPOSED"}
    before = deepcopy(proposal)
    c.assertEqual(m.confirm(proposal, True, "u2"), "denied")
    c.assertEqual(proposal, before)
    c.assertEqual(m.confirm(proposal, None, "u1"), "pending")
    c.assertEqual(proposal, before)
    c.assertEqual(m.confirm(proposal, True, "u1"), "executed")
    c.assertEqual(proposal["status"], "EXECUTED")
    c.assertEqual(m.confirm(proposal, True, "u1"), "already_executed")
    c.assertEqual(m.confirm(proposal, True, "u2"), "denied")
    rejected = {"id": "p2", "owner": "u1", "status": "PROPOSED"}
    c.assertEqual(m.confirm(rejected, False, "u1"), "rejected")
    c.assertEqual(rejected["status"], "REJECTED")
    c.assertEqual(m.confirm(rejected, True, "u1"), "rejected")
    with c.assertRaises(ValueError):
        m.confirm({"id": "p3", "owner": "u1", "status": "PROPOSED"}, "yes", "u1")


def check_guard(m, c):
    c.assertEqual(m.ngram_coverage("aaaaa", "aaaaab"), 0.5)
    c.assertEqual(m.ngram_coverage("完全相同的文本", "完全相同的文本"), 1.0)
    c.assertEqual(m.ngram_coverage("abc", "xyz"), 0.0)
    c.assertEqual(m.ngram_coverage("abcdef", "bc", 4), 1.0)
    c.assertEqual(m.ngram_coverage("", ""), 1.0)
    c.assertEqual(m.ngram_coverage("", "abcd"), 0.0)
    with c.assertRaises(ValueError):
        m.ngram_coverage("a", "a", 0)


def check_reflection(m, c):
    calls = []
    def good_rewrite(draft):
        c.assertIs(draft["tools_enabled"], False)
        calls.append(deepcopy(draft))
        return {"text": "过去的记录", "error": None}
    draft = {"text": "旧记录", "stage": "REPLY", "error": "MISSING_TIME_ATTRIBUTION"}
    before = deepcopy(draft)
    c.assertEqual(m.rewrite_once(draft, good_rewrite),
                  {"status": "completed", "text": "过去的记录", "rewrites": 1})
    c.assertEqual(draft, before)
    c.assertEqual(len(calls), 1)
    for stage, error in [("CLOSING", "MISSING_TIME_ATTRIBUTION"), ("REPLY", "TOOL_ERROR")]:
        result = m.rewrite_once(dict(draft, stage=stage, error=error), good_rewrite)
        c.assertEqual(result, {"status": "fallback", "text": "无法可靠回答", "rewrites": 0})
    c.assertEqual(len(calls), 1, "Ineligible failures do not invoke rewrite")
    c.assertEqual(m.rewrite_once(dict(draft, error=None), good_rewrite),
                  {"status": "completed", "text": "旧记录", "rewrites": 0})
    bad_calls = []
    def bad_rewrite(value):
        bad_calls.append(value)
        return draft
    c.assertEqual(m.rewrite_once(draft, bad_rewrite),
                  {"status": "fallback", "text": "无法可靠回答", "rewrites": 1})
    c.assertEqual(len(bad_calls), 1)
    def failed_rewrite(value):
        raise RuntimeError("synthetic provider failure")
    with c.assertRaises(RuntimeError):
        m.rewrite_once(draft, failed_rewrite)


def check_rpc(m, c):
    tools = {"add": lambda a, b: a + b}
    request = {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
    c.assertEqual(m.handle_rpc(request, tools), {"jsonrpc": "2.0", "id": 7, "result": {"tools": ["add"]}})
    call = dict(request, method="tools/call", params={"name": "add", "arguments": {"a": 2, "b": 3}})
    c.assertEqual(m.handle_rpc(call, tools), {"jsonrpc": "2.0", "id": 7, "result": 5})
    for bad, code in [(dict(request, method="unknown"), -32601),
                      (dict(call, params={"name": "missing", "arguments": {}}), -32602)]:
        result = m.handle_rpc(bad, tools)
        c.assertEqual(result["id"], 7)
        c.assertEqual(result["error"]["code"], code)


def check_trace(m, c):
    metadata = {"trace_id": "t1", "step": 1, "tool": "add", "status": "ok", "duration_ms": 5}
    event = dict(metadata, prompt="private", arguments={"text": "private"}, result="private", api_key="fake-secret")
    before = deepcopy(event)
    c.assertEqual(m.redact_event(event), metadata)
    c.assertEqual(m.redact_event({"prompt": "private"}), {})
    c.assertEqual(event, before)


def check_evaluation(m, c):
    cases = [{"expected": "completed", "actual": "completed", "steps": 2, "max_steps": 2},
             {"expected": "completed", "actual": "completed", "steps": 3, "max_steps": 2},
             {"expected": "completed", "actual": "failed", "steps": 1, "max_steps": 2}]
    c.assertEqual(m.evaluate(cases), {"total": 3, "passed": 1, "pass_rate": 1 / 3})
    c.assertEqual(m.evaluate([]), {"total": 0, "passed": 0, "pass_rate": 0.0})


def check_budget(m, c):
    c.assertEqual(m.remaining_budget(24000, 23500, 2000), {"remaining_ms": 500, "allowed": False})
    c.assertEqual(m.remaining_budget(24000, 22000, 2000), {"remaining_ms": 2000, "allowed": True})
    c.assertEqual(m.remaining_budget(24000, 24000), {"remaining_ms": 0, "allowed": False})
    c.assertEqual(m.remaining_budget(24000, 25000), {"remaining_ms": 0, "allowed": False})
    with c.assertRaises(ValueError):
        m.remaining_budget(10, 0, -1)


CHECKS = dict(zip((f"A{i:02d}" for i in range(1, 14)),
                  (check_loop, check_dispatch, check_observation, check_transition, check_context,
                   check_memory, check_confirmation, check_guard, check_reflection, check_rpc,
                   check_trace, check_evaluation, check_budget)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exercise", required=True, choices=sorted(CHECKS))
    parser.add_argument("--submission", required=True, type=Path)
    args = parser.parse_args()
    try:
        path = args.submission.resolve()
        spec = importlib.util.spec_from_file_location("_linsist_student", path)
        if spec is None or spec.loader is None:
            raise ValueError("Submission must be an importable Python file")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        CHECKS[args.exercise](module, unittest.TestCase())
    except Exception as error:
        print(f"FAIL [{args.exercise}]: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"exercise": args.exercise, "status": "passed", "mode": "offline_contract"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
