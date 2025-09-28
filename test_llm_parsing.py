#!/usr/bin/env python3
"""Test script for LLMChatSession parsing logic."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from model.llm_chat_session import LLMChatSession

def test_parse_response_content():
    """Test the _parse_response_content method with various inputs."""

    # Create a dummy session to access the method
    session = LLMChatSession("test_user", {"node": "test"})

    test_cases = [
        # Normal case: content with <think> and </think>
        {
            "name": "normal_think_block",
            "input": "<think>This is internal reasoning</think>This is the final answer.",
            "expected": "This is the final answer.",
            "description": "Normal case with properly closed think block"
        },
        # Edge case: unclosed <think> tag
        {
            "name": "unclosed_think",
            "input": "<think>This is internal reasoning without closing tag",
            "expected": "",
            "description": "Unclosed think tag should remove everything from <think> onwards"
        },
        # Edge case: multiple think blocks
        {
            "name": "multiple_think_blocks",
            "input": "<think>First thought</think>Some text<think>Second thought</think>Final answer.",
            "expected": "Some textFinal answer.",
            "description": "Multiple think blocks should all be removed"
        },
        # Edge case: no think tags
        {
            "name": "no_think_tags",
            "input": "This is a normal response without any think tags.",
            "expected": "This is a normal response without any think tags.",
            "description": "Content without think tags should remain unchanged"
        },
        # Edge case: empty content
        {
            "name": "empty_content",
            "input": "",
            "expected": "",
            "description": "Empty content should return empty string"
        },
        # Edge case: case insensitive tags
        {
            "name": "case_insensitive",
            "input": "<THINK>Mixed case thinking</THINK>Final answer.",
            "expected": "Final answer.",
            "description": "Tags should be case insensitive"
        },
        # Edge case: nested think blocks (regex handles this)
        {
            "name": "nested_think",
            "input": "<think>Outer<think>Inner</think>still outer</think>Answer.",
            "expected": "Answer.",
            "description": "Nested think blocks should be handled by regex"
        },
        # Edge case: think at end
        {
            "name": "think_at_end",
            "input": "Some answer<think>thinking at end",
            "expected": "Some answer",
            "description": "Think block at end should be removed"
        },
        # Edge case: only think content
        {
            "name": "only_think",
            "input": "<think>Only thinking, no answer</think>",
            "expected": "",
            "description": "Content with only think block should result in empty string"
        },
        # Edge case: think with special characters
        {
            "name": "special_chars",
            "input": "<think>Thinking with\nnewlines\tand tabs</think>Answer with émojis 🚀",
            "expected": "Answer with émojis 🚀",
            "description": "Special characters and unicode should be preserved"
        }
    ]

    results = []
    all_passed = True

    print("Testing _parse_response_content method...")
    print("=" * 60)

    for test_case in test_cases:
        try:
            result = session._parse_response_content(test_case["input"])
            passed = result == test_case["expected"]

            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{status} {test_case['name']}")
            print(f"  Description: {test_case['description']}")
            print(f"  Input: {repr(test_case['input'])}")
            print(f"  Expected: {repr(test_case['expected'])}")
            print(f"  Got: {repr(result)}")

            if not passed:
                all_passed = False
                print(f"  ❌ MISMATCH!")

            print()

            results.append({
                "name": test_case["name"],
                "passed": passed,
                "expected": test_case["expected"],
                "got": result
            })

        except Exception as e:
            print(f"💥 ERROR in {test_case['name']}: {e}")
            all_passed = False
            results.append({
                "name": test_case["name"],
                "passed": False,
                "error": str(e)
            })
            print()

    print("=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED!")
        failed_count = sum(1 for r in results if not r.get("passed", False))
        print(f"Failed tests: {failed_count}/{len(results)}")

    return all_passed, results

def test_integration_points():
    """Test that integration points use the parsing correctly."""
    print("\nTesting integration points...")
    print("=" * 60)

    # Check that chat_with_tools and chat_without_tools use _parse_response_content
    session = LLMChatSession("test_user", {"node": "test"})

    # We can't actually call chat methods without Ollama running,
    # but we can verify the methods exist and check their structure
    import inspect

    chat_with_tools_source = inspect.getsource(session.chat_with_tools)
    chat_without_tools_source = inspect.getsource(session.chat_without_tools)

    with_tools_uses_parsing = "_parse_response_content" in chat_with_tools_source
    without_tools_uses_parsing = "_parse_response_content" in chat_without_tools_source

    print(f"chat_with_tools uses _parse_response_content: {'✅ YES' if with_tools_uses_parsing else '❌ NO'}")
    print(f"chat_without_tools uses _parse_response_content: {'✅ YES' if without_tools_uses_parsing else '❌ NO'}")

    integration_ok = with_tools_uses_parsing and without_tools_uses_parsing

    if integration_ok:
        print("🎉 Integration points correctly use parsing!")
    else:
        print("⚠️  Integration points may not be using parsing correctly!")

    return integration_ok

def run_existing_tests():
    """Run existing test suites to check for regressions."""
    print("\nRunning existing tests for regressions...")
    print("=" * 60)

    import subprocess
    import os

    test_files = [
        "test_db.py",
        "test_api.py",
        "test_system_integration.py",
        "test_comprehensive_suite.py"
    ]

    results = []

    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"Running {test_file}...")
            try:
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                passed = result.returncode == 0
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"{status} {test_file}")

                if not passed:
                    print(f"  stdout: {result.stdout}")
                    print(f"  stderr: {result.stderr}")

                results.append({
                    "file": test_file,
                    "passed": passed,
                    "returncode": result.returncode
                })

            except subprocess.TimeoutExpired:
                print(f"⏰ TIMEOUT {test_file}")
                results.append({
                    "file": test_file,
                    "passed": False,
                    "error": "Timeout"
                })
            except Exception as e:
                print(f"💥 ERROR {test_file}: {e}")
                results.append({
                    "file": test_file,
                    "passed": False,
                    "error": str(e)
                })
        else:
            print(f"⚠️  SKIPPED {test_file} (file not found)")
            results.append({
                "file": test_file,
                "passed": True,  # Not a regression if file doesn't exist
                "skipped": True
            })

    all_passed = all(r["passed"] for r in results)
    if all_passed:
        print("🎉 No regressions detected in existing tests!")
    else:
        print("⚠️  Regressions detected in existing tests!")

    return all_passed, results

def main():
    """Main test function."""
    print("🧪 Testing LLMChatSession Parsing Fix")
    print("Focus: <think> tag removal and clean answer extraction")
    print()

    # Test the parsing logic
    parsing_passed, parsing_results = test_parse_response_content()

    # Test integration points
    integration_passed = test_integration_points()

    # Run existing tests for regressions
    regression_passed, regression_results = run_existing_tests()

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    print(f"Parsing Logic Tests: {'✅ PASSED' if parsing_passed else '❌ FAILED'}")
    print(f"Integration Points: {'✅ PASSED' if integration_passed else '❌ FAILED'}")
    print(f"Regression Tests: {'✅ PASSED' if regression_passed else '❌ FAILED'}")

    overall_success = parsing_passed and integration_passed and regression_passed

    if overall_success:
        print("\n🎉 ALL TESTS PASSED! The parsing fix is working correctly.")
    else:
        print("\n⚠️  SOME ISSUES FOUND! Review the details above.")

    # Detailed parsing results
    if not parsing_passed:
        print("\n❌ PARSING TEST DETAILS:")
        for result in parsing_results:
            if not result.get("passed", False):
                print(f"  • {result['name']}: FAILED")
                if "error" in result:
                    print(f"    Error: {result['error']}")
                else:
                    print(f"    Expected: {repr(result['expected'])}")
                    print(f"    Got: {repr(result['got'])}")

    # Regression details
    if not regression_passed:
        print("\n❌ REGRESSION TEST DETAILS:")
        for result in regression_results:
            if not result.get("passed", False):
                print(f"  • {result['file']}: FAILED")
                if "error" in result:
                    print(f"    Error: {result['error']}")

    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)