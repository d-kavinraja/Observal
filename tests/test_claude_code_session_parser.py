# SPDX-FileCopyrightText: 2026 Madhumidha <madhumidha072005@gmail.com>
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for Claude Code session parser."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "observal-server"))

from services.session_parsers.claude_code import parse_rows

# ── Sample Claude Code JSONL lines ────────────────────────────────────────────

USER_SIMPLE = '{"type":"user","message":{"content":"Hello world"},"timestamp":"2026-06-01T10:00:00.000Z"}'
USER_LIST_TEXT = '{"type":"user","message":{"content":[{"type":"text","text":"Hello"},{"type":"text","text":"world"}]},"timestamp":"2026-06-01T10:00:01.000Z"}'
USER_TOOL_RESULT = '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tool_123","content":"file contents here"}]},"timestamp":"2026-06-01T10:00:02.000Z"}'
USER_TOOL_RESULT_LIST = '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"tool_123","content":[{"type":"text","text":"file contents"}]}]},"timestamp":"2026-06-01T10:00:02.000Z"}'

ASSISTANT_TEXT = '{"type":"assistant","message":{"content":[{"type":"text","text":"I am Claude."}],"model":"claude-3","stop_reason":"end_turn","usage":{"input_tokens":10,"output_tokens":20,"cache_read_input_tokens":5,"cache_creation_input_tokens":2}},"timestamp":"2026-06-01T10:00:05.000Z"}'
ASSISTANT_THINKING = '{"type":"assistant","message":{"content":[{"type":"thinking","thinking":"Hmm, I should use a tool."},{"type":"text","text":"Okay!"}]},"timestamp":"2026-06-01T10:00:06.000Z"}'
ASSISTANT_TOOL_USE = '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"tool_123","name":"read_file","input":{"path":"/tmp/foo.txt"}}]},"timestamp":"2026-06-01T10:00:07.000Z"}'
ASSISTANT_TOOL_USAGE_ONLY = '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"tool_123","name":"read_file","input":{}}],"usage":{"input_tokens":5}},"timestamp":"2026-06-01T10:00:08.000Z"}'

SYSTEM_EVENT = '{"type":"system","content":"Initializing system...","timestamp":"2026-06-01T09:59:59.000Z"}'
ATTACHMENT_EVENT = '{"type":"attachment","attachment":{"name":"config.json","type":"application/json"},"timestamp":"2026-06-01T10:00:00.000Z"}'

META_EVENT = '{"type":"meta","foo":"bar"}'
AGENT_SETTING_EVENT = '{"type":"agent-setting","setting":"value"}'

ASSISTANT_MULTIPLE_TEXT = '{"type":"assistant","message":{"content":[{"type":"text","text":"Part 1"},{"type":"text","text":"Part 2"}]},"timestamp":"2026-06-01T10:00:09.000Z"}'
ASSISTANT_MULTIPLE_TOOLS = '{"type":"assistant","message":{"content":[{"type":"tool_use","id":"tool_1","name":"read"},{"type":"tool_use","id":"tool_2","name":"write"}]},"timestamp":"2026-06-01T10:00:10.000Z"}'
ASSISTANT_THINK_TOOL_TEXT = '{"type":"assistant","message":{"content":[{"type":"thinking","thinking":"Hmm"},{"type":"tool_use","id":"tool_1","name":"read"},{"type":"text","text":"Done"}]},"timestamp":"2026-06-01T10:00:11.000Z"}'
MISSING_MESSAGE = '{"type":"assistant","timestamp":"2026-06-01T10:00:12.000Z"}'
MALFORMED_CONTENT = '{"type":"user","message":{"content":123},"timestamp":"2026-06-01T10:00:13.000Z"}'
MISSING_TIMESTAMP = '{"type":"user","message":{"content":"No time"}}'
USER_UNKNOWN_TOOL_RESULT = '{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"unknown_tool","content":"missing"}]},"timestamp":"2026-06-01T10:00:14.000Z"}'


class TestClaudeCodeSessionParser:
    def test_parse_empty_rows(self):
        assert parse_rows([]) == []

    def test_invalid_json(self):
        rows = [{"raw_line": "not valid json", "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == ""

    def test_empty_raw_line(self):
        rows = [{"raw_line": "", "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == ""

    def test_meta_event_skipped(self):
        rows = [{"raw_line": META_EVENT}, {"raw_line": AGENT_SETTING_EVENT}]
        events = parse_rows(rows)
        assert events == []

    def test_user_prompt_simple(self):
        rows = [{"raw_line": USER_SIMPLE, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_userpromptsubmit"
        assert events[0]["body"] == "Hello world"
        assert events[0]["attributes"]["tool_input"] == "Hello world"

    def test_user_prompt_list_text(self):
        rows = [{"raw_line": USER_LIST_TEXT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_userpromptsubmit"
        assert events[0]["body"] == "Hello\nworld"
        assert events[0]["attributes"]["tool_input"] == "Hello\nworld"

    def test_assistant_response_text_with_usage(self):
        rows = [{"raw_line": ASSISTANT_TEXT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_assistant_response"
        assert events[0]["body"] == "I am Claude."
        attrs = events[0]["attributes"]
        assert attrs["input_tokens"] == "10"
        assert attrs["output_tokens"] == "20"
        assert attrs["cache_read_tokens"] == "5"
        assert attrs["cache_creation_tokens"] == "2"
        assert attrs["model"] == "claude-3"
        assert attrs["stop_reason"] == "end_turn"

    def test_assistant_thinking(self):
        rows = [{"raw_line": ASSISTANT_THINKING, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 2
        assert events[0]["event_name"] == "hook_assistant_thinking"
        assert events[0]["body"] == "Hmm, I should use a tool."

        assert events[1]["event_name"] == "hook_assistant_response"
        assert events[1]["body"] == "Okay!"

    def test_assistant_tool_use(self):
        rows = [{"raw_line": ASSISTANT_TOOL_USE, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_posttooluse"
        assert events[0]["body"] == "read_file"
        assert events[0]["attributes"]["tool_name"] == "read_file"
        assert events[0]["attributes"]["tool_use_id"] == "tool_123"

    def test_assistant_tool_usage_only_emits_token_usage_event(self):
        # A turn with only tool_use and token usage should emit a token_usage event
        rows = [{"raw_line": ASSISTANT_TOOL_USAGE_ONLY, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 2
        assert events[0]["event_name"] == "hook_posttooluse"
        assert events[1]["event_name"] == "hook_token_usage"
        assert events[1]["attributes"]["input_tokens"] == "5"

    def test_tool_result_merging(self):
        rows = [
            {"raw_line": ASSISTANT_TOOL_USE, "ide": "claude-code"},
            {"raw_line": USER_TOOL_RESULT, "ide": "claude-code"},
        ]
        events = parse_rows(rows)
        # Expected: 1 event for the tool use, and 0 standalone for the result (result is merged back into the tool use event)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_posttooluse"
        assert events[0]["attributes"]["tool_response"] == "file contents here"

    def test_tool_result_list_merging(self):
        rows = [
            {"raw_line": ASSISTANT_TOOL_USE, "ide": "claude-code"},
            {"raw_line": USER_TOOL_RESULT_LIST, "ide": "claude-code"},
        ]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_posttooluse"
        assert events[0]["attributes"]["tool_response"] == "file contents"

    def test_orphan_tool_result_is_skipped(self):
        rows = [{"raw_line": USER_TOOL_RESULT, "ide": "claude-code"}]
        events = parse_rows(rows)
        # An orphan tool result without an existing tool use in the same batch(currently does not emit anything or is silently dropped)
        assert len(events) == 0

    def test_system_event(self):
        rows = [{"raw_line": SYSTEM_EVENT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "hook_sessionstart"
        assert events[0]["body"] == "Initializing system..."

    def test_attachment_event(self):
        rows = [{"raw_line": ATTACHMENT_EVENT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == "attachment"
        assert events[0]["body"] == "config.json"
        assert events[0]["attributes"]["attachment_name"] == "config.json"
        assert events[0]["attributes"]["attachment_type"] == "application/json"

    def test_unrecognized_event_type(self):
        rows = [{"raw_line": '{"type":"unknown"}', "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 1
        assert events[0]["event_name"] == ""

    def test_assistant_multiple_text_blocks(self):
        rows = [{"raw_line": ASSISTANT_MULTIPLE_TEXT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 2
        assert events[0]["body"] == "Part 1"
        assert events[1]["body"] == "Part 2"

    def test_assistant_multiple_tools(self):
        rows = [{"raw_line": ASSISTANT_MULTIPLE_TOOLS, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 2
        assert events[0]["attributes"]["tool_name"] == "read"
        assert events[1]["attributes"]["tool_name"] == "write"

    def test_unknown_tool_result_does_not_crash(self):
        rows = [
            {"raw_line": ASSISTANT_MULTIPLE_TOOLS, "ide": "claude-code"},
            {"raw_line": USER_UNKNOWN_TOOL_RESULT, "ide": "claude-code"},
        ]
        events = parse_rows(rows)
        assert len(events) == 2

    def test_missing_timestamp_uses_ingested_at(self):
        rows = [
            {
                "raw_line": MISSING_TIMESTAMP,
                "timestamp": "1970-01-01 00:00:00",
                "ingested_at": "2026-06-01 10:00:15.000",
                "ide": "claude-code",
            }
        ]
        events = parse_rows(rows)
        assert events[0]["timestamp"] == "2026-06-01 10:00:15.000"

    def test_missing_message_field(self):
        rows = [{"raw_line": MISSING_MESSAGE, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 0

    def test_malformed_content(self):
        rows = [{"raw_line": MALFORMED_CONTENT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 0

    def test_assistant_think_tool_text(self):
        rows = [{"raw_line": ASSISTANT_THINK_TOOL_TEXT, "ide": "claude-code"}]
        events = parse_rows(rows)
        assert len(events) == 3
        assert events[0]["event_name"] == "hook_assistant_thinking"
        assert events[1]["event_name"] == "hook_posttooluse"
        assert events[2]["event_name"] == "hook_assistant_response"
