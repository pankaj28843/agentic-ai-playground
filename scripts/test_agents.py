#!/usr/bin/env python3
"""Consolidated agent testing script.

Supports both simulated and real agent testing modes for validation.
"""

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

# Complex TechDocs test queries for validation
COMPLEX_TEST_QUERIES = [
    "How to implement Django file uploads with libraries that need file paths, including proper cleanup and error handling?",
    "Compare React useEffect cleanup patterns with Vue.js lifecycle methods for memory leak prevention",
    "Design a FastAPI middleware for request tracing that works with async/await and handles database connections properly",
    "Implement PostgreSQL connection pooling in Python with proper transaction management and error recovery",
    "Create a TypeScript generic utility type that preserves literal types while allowing optional properties",
]


def assess_response_quality(query: str, response: str) -> float:
    """Assess response quality based on multiple criteria."""
    criteria = {
        "completeness": assess_completeness(query, response),
        "accuracy": assess_accuracy(response),
        "tool_usage": assess_tool_usage(response),
        "citations": assess_citations(response),
        "clarity": assess_clarity(response),
        "tool_authenticity": assess_tool_authenticity(response),
        "parallel_execution": assess_parallel_execution(response),
        "progressive_disclosure": assess_progressive_disclosure(response),
    }
    return sum(criteria.values()) / len(criteria)


def assess_tool_authenticity(response: str) -> float:
    """Check for tool role-playing anti-patterns."""
    # Look for fake tool outputs or role-playing
    fake_patterns = [
        r"Response:\s*\[.*?\]",  # "Response: [fake data]"
        r"Tool output:\s*\{.*?\}",  # "Tool output: {fake json}"
        r"The tool returns:\s*",  # "The tool returns: ..."
        r"Tool call result:\s*",  # "Tool call result: ..."
        r"API response:\s*\{",  # "API response: {fake}"
    ]

    fake_count = sum(len(re.findall(pattern, response, re.IGNORECASE)) for pattern in fake_patterns)

    # Penalize fake patterns heavily
    if fake_count > 0:
        return max(0.0, 1.0 - (fake_count * 0.3))

    # Look for authentic tool usage indicators
    authentic_patterns = [
        r"TechDocs-find_tenant",
        r"TechDocs-root_search",
        r"TechDocs-root_fetch",
        r"Tool call:",
        r"Tool result:",
    ]

    authentic_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE)) for pattern in authentic_patterns
    )
    return min(1.0, authentic_count * 0.2)


def assess_parallel_execution(response: str) -> float:
    """Check for evidence of parallel tool execution."""
    parallel_indicators = [
        r"parallel",
        r"simultaneously",
        r"concurrent",
        r"multiple.*calls",
        r"batch.*operations",
    ]

    parallel_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE)) for pattern in parallel_indicators
    )
    return min(1.0, parallel_count * 0.3)


def assess_progressive_disclosure(response: str) -> float:
    """Check for progressive disclosure patterns."""
    disclosure_patterns = [
        r"first.*then",
        r"start.*with",
        r"begin.*by",
        r"initially",
        r"step.*by.*step",
    ]

    disclosure_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE)) for pattern in disclosure_patterns
    )
    return min(1.0, disclosure_count * 0.2)


def assess_completeness(query: str, response: str) -> float:
    """Assess if response addresses all aspects of the query."""
    # Extract key concepts from query
    query_words = set(re.findall(r"\b\w+\b", query.lower()))
    response_words = set(re.findall(r"\b\w+\b", response.lower()))

    # Calculate coverage of query concepts in response
    if not query_words:
        return 1.0

    coverage = len(query_words.intersection(response_words)) / len(query_words)
    return min(1.0, coverage * 1.5)  # Boost for good coverage


def assess_accuracy(response: str) -> float:
    """Assess technical accuracy indicators."""
    # Look for specific technical details and code examples
    accuracy_indicators = [
        r"```\w+",  # Code blocks
        r"import\s+\w+",  # Import statements
        r"def\s+\w+",  # Function definitions
        r"class\s+\w+",  # Class definitions
        r"https?://[^\s]+",  # URLs
        r"\w+\.\w+\(",  # Method calls
    ]

    accuracy_count = sum(len(re.findall(pattern, response)) for pattern in accuracy_indicators)
    return min(1.0, accuracy_count * 0.1)


def assess_tool_usage(response: str) -> float:
    """Assess appropriate tool usage."""
    tool_patterns = [
        r"TechDocs-\w+",
        r"Tool call",
        r"search.*documentation",
        r"fetch.*page",
    ]

    tool_count = sum(len(re.findall(pattern, response, re.IGNORECASE)) for pattern in tool_patterns)
    return min(1.0, tool_count * 0.2)


def assess_citations(response: str) -> float:
    """Assess presence of proper citations."""
    citation_patterns = [
        r"https?://[^\s]+",  # URLs
        r"Source:",
        r"Reference:",
        r"According to",
        r"Based on",
    ]

    citation_count = sum(
        len(re.findall(pattern, response, re.IGNORECASE)) for pattern in citation_patterns
    )
    return min(1.0, citation_count * 0.2)


def assess_clarity(response: str) -> float:
    """Assess response clarity and structure."""
    # Look for good structure indicators
    structure_patterns = [
        r"^#+\s",  # Headers
        r"^\d+\.",  # Numbered lists
        r"^[-*]\s",  # Bullet points
        r"```",  # Code blocks
    ]

    structure_count = sum(
        len(re.findall(pattern, response, re.MULTILINE)) for pattern in structure_patterns
    )

    # Penalize very short or very long responses
    length_penalty = 0.0
    if len(response) < 100:
        length_penalty = 0.3
    elif len(response) > 5000:
        length_penalty = 0.2

    clarity_score = min(1.0, structure_count * 0.1) - length_penalty
    return max(0.0, clarity_score)


async def test_real_agent_response(profile_name: str, query: str) -> dict[str, Any]:
    """Test real agent response using actual runtime."""
    try:
        from agent_toolkit.config.execution_mode import get_execution_mode_resolver  # noqa: PLC0415
        from agent_toolkit.runtime import AgentRuntime  # noqa: PLC0415

        resolver = get_execution_mode_resolver()
        public_profiles = resolver.get_public_profiles()
        runtime = AgentRuntime()

        if profile_name not in public_profiles:
            return {
                "profile": profile_name,
                "query": query,
                "error": f"Public profile {profile_name} not found",
                "quality_score": 0.0,
            }

        invocation_state = runtime.build_invocation_state(
            "",
            "test-session",
            run_mode=profile_name,
            profile_name=profile_name,
        )

        # Execute query and measure response
        start_time = time.time()
        response = runtime.run(profile_name, profile_name, query, invocation_state, "test-session")
        response_time = time.time() - start_time

        # Assess quality
        quality_score = assess_response_quality(query, str(response))

        return {
            "profile": profile_name,
            "query": query,
            "response": str(response),
            "response_time": response_time,
            "quality_score": quality_score,
        }

    except Exception as e:  # noqa: BLE001 - test script needs broad exception handling
        return {
            "profile": profile_name,
            "query": query,
            "error": str(e),
            "quality_score": 0.0,
        }


def test_simulated_response(profile_name: str, query: str) -> dict[str, Any]:
    """Test with simulated response for development/testing."""
    # Simulate a response based on profile type
    if "research" in profile_name.lower():
        response = f"""I'll help you with {query}. Let me search the documentation for comprehensive information.

TechDocs-find_tenant: django, react, fastapi
TechDocs-root_search: {query[:50]}...
TechDocs-root_fetch: https://docs.example.com/guide

Based on the documentation, here's a comprehensive approach:

1. **Initial Setup**
   ```python
   # Example implementation
   def setup_feature():
       pass
   ```

2. **Implementation Details**
   - Key consideration A
   - Key consideration B
   - Best practices

3. **Error Handling**
   - Common pitfalls
   - Recovery strategies

**References:**
- https://docs.example.com/guide
- https://docs.example.com/api

This approach ensures proper implementation while following best practices."""

    elif "quick" in profile_name.lower():
        response = f"""Here's a quick solution for {query}:

```python
# Quick implementation
def quick_solution():
    # Implementation here
    pass
```

Key points:
- Main approach
- Important consideration
- Quick tip

Reference: https://docs.example.com/quickstart"""

    else:
        response = f"""I'll analyze {query} comprehensively.

**Analysis Phase:**
TechDocs-find_tenant: relevant-docs
TechDocs-root_search: detailed analysis

**Implementation Strategy:**
1. Foundation setup
2. Core implementation
3. Testing and validation

**Code Example:**
```python
class Solution:
    def implement(self):
        # Detailed implementation
        pass
```

**Validation:**
- Test case A
- Test case B
- Performance considerations

**References:**
- https://docs.example.com/advanced
- https://docs.example.com/patterns"""

    # Simulate response time
    response_time = len(response) * 0.01  # Simulate typing speed

    # Assess quality
    quality_score = assess_response_quality(query, response)

    return {
        "profile": profile_name,
        "query": query,
        "response": response,
        "response_time": response_time,
        "quality_score": quality_score,
        "simulated": True,
    }


async def run_test_suite(mode: str, profiles: list[str], queries: list[str]) -> None:
    """Run the complete test suite."""
    results = []

    print(f"Running test suite in {mode} mode...")
    print(f"Profiles: {', '.join(profiles)}")
    print(f"Queries: {len(queries)}")
    print("-" * 60)

    for profile in profiles:
        for i, query in enumerate(queries, 1):
            print(f"Testing {profile} - Query {i}/{len(queries)}")
            print(f"Query: {query[:60]}...")

            if mode == "real":
                result = await test_real_agent_response(profile, query)
            else:
                result = test_simulated_response(profile, query)

            results.append(result)

            if "error" in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(
                    f"✅ Quality: {result['quality_score']:.2f}, Time: {result['response_time']:.1f}s"
                )

            print()

    # Summary
    successful_results = [r for r in results if "error" not in r]
    if successful_results:
        avg_quality = sum(r["quality_score"] for r in successful_results) / len(successful_results)
        avg_time = sum(r["response_time"] for r in successful_results) / len(successful_results)

        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total tests: {len(results)}")
        print(f"Successful: {len(successful_results)}")
        print(f"Failed: {len(results) - len(successful_results)}")
        print(f"Average quality score: {avg_quality:.2f}")
        print(f"Average response time: {avg_time:.1f}s")

        # Save results
        output_file = Path(f"test_results_{mode}_{int(time.time())}.json")
        with output_file.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test agent responses")
    parser.add_argument(
        "--mode",
        choices=["real", "simulated"],
        default="simulated",
        help="Test mode: real (uses actual runtime) or simulated (mock responses)",
    )
    parser.add_argument("--profiles", nargs="+", default=None, help="Profiles to test")
    parser.add_argument(
        "--queries", nargs="+", help="Custom queries to test (overrides default complex queries)"
    )
    parser.add_argument("--single-query", help="Test a single query across all profiles")

    args = parser.parse_args()

    # Determine queries to use
    if args.single_query:
        queries = [args.single_query]
    elif args.queries:
        queries = args.queries
    else:
        queries = COMPLEX_TEST_QUERIES

    profiles = args.profiles
    if not profiles:
        from agent_toolkit.config.execution_mode import get_execution_mode_resolver  # noqa: PLC0415

        resolver = get_execution_mode_resolver()
        profiles = list(resolver.get_public_profiles().keys())

    # Run the test suite
    asyncio.run(run_test_suite(args.mode, profiles, queries))


if __name__ == "__main__":
    main()
