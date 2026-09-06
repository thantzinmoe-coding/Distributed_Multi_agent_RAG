from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from packages.contracts.api import GenerateRequest, GenerateResponse
from services.llm.app import OllamaProvider, generate


def request_fixture() -> GenerateRequest:
    return GenerateRequest(
        target_occupation="Developer",
        match_score=50,
        coverage_score=100,
        strengths=[],
        partial_skills=[],
        gaps=[],
        courses=[],
        evidence=[],
    )


class LlmFailoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_second_provider_when_first_fails(self) -> None:
        providers = [
            OllamaProvider("http://primary", "qwen3:4b"),
            OllamaProvider("http://fallback", "gemma4:latest"),
        ]
        fallback_result = GenerateResponse(
            summary="Grounded result",
            citations=["evidence-1"],
            mode="ollama:gemma4:latest",
            warnings=[],
        )
        call = AsyncMock(side_effect=[ConnectionError(), fallback_result])

        with (
            patch("services.llm.app.USE_OLLAMA", True),
            patch("services.llm.app.configured_providers", return_value=providers),
            patch("services.llm.app.generate_with_ollama", call),
        ):
            result = await generate(request_fixture())

        self.assertEqual(result.mode, "ollama:gemma4:latest")
        self.assertIn("qwen3:4b (ConnectionError)", result.warnings[-1])
        self.assertEqual(call.await_count, 2)

    async def test_uses_deterministic_result_only_after_all_providers_fail(self) -> None:
        providers = [
            OllamaProvider("http://primary", "qwen3:4b"),
            OllamaProvider("http://fallback", "gemma4:latest"),
        ]

        with (
            patch("services.llm.app.USE_OLLAMA", True),
            patch("services.llm.app.configured_providers", return_value=providers),
            patch("services.llm.app.generate_with_ollama", AsyncMock(side_effect=ConnectionError())),
        ):
            result = await generate(request_fixture())

        self.assertEqual(result.mode, "deterministic-fallback")
        self.assertIn("qwen3:4b", result.warnings[-1])
        self.assertIn("gemma4:latest", result.warnings[-1])


if __name__ == "__main__":
    unittest.main()
