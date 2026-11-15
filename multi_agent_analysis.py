# ============================================================
# multi_agent_analysis.py
# ============================================================
#
# CFAST Multi-Agent Question Answering Pipeline
#
# Flow:
#
#              USER QUESTION
#                    +
#               CFAST DATA
#                    |
#          -------------------
#          |                 |
#          v                 v
#       ANALYST A        ANALYST B
#          |                 |
#          -------+----------
#                 |
#                 v
#              JUDGE
#                 |
#                 v
#             FINAL ANSWER
#
# ============================================================


import json
import asyncio

from abc import ABC, abstractmethod
from typing import Any, Dict

from prompts import (
    ANALYST_A_PROMPT,
    ANALYST_B_PROMPT,
    JUDGE_PROMPT,
)


# ============================================================
# CONFIGURATION
# ============================================================

class Config:

    # Prevent sending extremely large files to the LLM.

    MAX_DATA_CHARS = 50000


# ============================================================
# BASE LLM CLIENT
# ============================================================

class BaseLLMClient(ABC):

    """
    Common interface for all LLM providers.

    Later you can create:

        GeminiClient
        LlamaClient
        GroqClient
        OpenRouterClient

    All clients must implement generate().
    """


    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:

        pass


# ============================================================
# MOCK LLM CLIENT
# ============================================================

class MockLLMClient(BaseLLMClient):

    """
    Temporary fake LLM.

    This lets you test the entire pipeline before connecting
    real Gemini or Llama APIs.
    """


    def __init__(self, name: str):

        self.name = name


    async def generate(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:

        print(f"\n🤖 {self.name} is processing...")


        # ----------------------------------------------------
        # ANALYST A
        # ----------------------------------------------------

        if self.name == "Analyst A":

            return json.dumps(
                {
                    "agent": "A",

                    "answer":
                        "Based on the provided CFAST data, "
                        "conditions change significantly during "
                        "the simulation.",

                    "key_insights": [
                        {
                            "insight":
                                "The simulation data shows "
                                "changing fire conditions over time.",

                            "evidence":
                                "Values in the provided CFAST "
                                "dataset change during the "
                                "simulation.",

                            "importance":
                                "high"
                        }
                    ],

                    "hazards": [],

                    "data_limitations": [
                        "This is currently a mock LLM response."
                    ],

                    "assumptions": []
                },
                indent=2
            )


        # ----------------------------------------------------
        # ANALYST B
        # ----------------------------------------------------

        if self.name == "Analyst B":

            return json.dumps(
                {
                    "agent": "B",

                    "answer":
                        "The CFAST data should be evaluated "
                        "for important trends and hazardous "
                        "conditions.",

                    "key_insights": [
                        {
                            "insight":
                                "Simulation variables should be "
                                "evaluated over time.",

                            "evidence":
                                "The provided dataset contains "
                                "time-dependent simulation data.",

                            "importance":
                                "medium"
                        }
                    ],

                    "hazards": [],

                    "data_limitations": [
                        "This is currently a mock LLM response."
                    ],

                    "assumptions": []
                },
                indent=2
            )


        # ----------------------------------------------------
        # JUDGE
        # ----------------------------------------------------

        return json.dumps(
            {
                "decision": "COMBINE",

                "reasoning":
                    "This is a temporary mock judge decision. "
                    "A real Judge LLM will evaluate the two "
                    "analyses against the original CFAST data.",

                "analyst_a_score": {
                    "accuracy": 7,
                    "evidence": 7,
                    "relevance": 7,
                    "reliability": 7
                },

                "analyst_b_score": {
                    "accuracy": 7,
                    "evidence": 7,
                    "relevance": 7,
                    "reliability": 7
                },

                "final_answer":
                    "Temporary combined answer generated by "
                    "the mock multi-agent pipeline.",

                "approved_insights": [
                    "Real LLM-generated insights will appear here."
                ],

                "approved_hazards": [],

                "limitations": [
                    "Mock LLM clients are currently being used."
                ],

                "problems_found": []
            },
            indent=2
        )


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_response(
    response: str
) -> Dict[str, Any]:

    """
    Parse JSON returned by an LLM.

    Also handles:

        ```json
        {...}
        ```
    """

    cleaned = response.strip()


    if cleaned.startswith("```json"):

        cleaned = cleaned[len("```json"):]


    elif cleaned.startswith("```"):

        cleaned = cleaned[len("```"):]


    if cleaned.endswith("```"):

        cleaned = cleaned[:-3]


    cleaned = cleaned.strip()


    try:

        return json.loads(cleaned)


    except json.JSONDecodeError:

        return {
            "parse_error": True,
            "raw_response": response
        }

