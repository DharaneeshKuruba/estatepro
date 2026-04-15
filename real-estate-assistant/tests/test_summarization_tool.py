import pytest

from tests.helpers import build_tool_cases, execute_tool_case

TOOL_NAME = "summarization"
CASES = build_tool_cases(TOOL_NAME)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_summarization_cases(client, case):
    execute_tool_case(client, case, TOOL_NAME)
