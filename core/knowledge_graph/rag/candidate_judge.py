from __future__ import annotations

import json
from typing import Dict, Any

from core.knowledge_graph.rag.llm_orchestrator import AzureLLMOrchestrator


class CandidateJudge:
    """
    Uses the LLM to determine whether a candidate KnownIssue
    actually matches the user query.
    """

    MIN_CONFIDENCE = 0.75

    def __init__(self):
        self.llm = AzureLLMOrchestrator()

    def judge(self, user_query: str, issue_id: str, issue_context: Dict[str, Any]) -> Dict[str, Any]:
        issue = issue_context.get("issue", {})

        symptoms = issue.get("symptoms", "")
        root_cause = issue.get("root_cause", "")
        workaround = issue.get("workaround", "")
        title = issue.get("title", "")
        description = issue.get("description", "")

        prompt = f"""
You are a strict troubleshooting classifier.

Your job is to decide whether the candidate KnownIssue REALLY matches the user's problem.

IMPORTANT RULES:
- Only return match=true if the issue is clearly about the same problem.
- If the user query is vague, generic, unrelated, or missing key overlap, return match=false.
- Do NOT infer hidden product context from previous conversations.
- Do NOT accept based on one weak keyword.
- If uncertain, return match=false.

User Query:
{user_query}

Candidate Issue ID:
{issue_id}

Candidate Title:
{title}

Candidate Description:
{description}

Symptoms:
{symptoms}

Root Cause:
{root_cause}

Workaround:
{workaround}

Respond ONLY with valid JSON:
{{
  "match": true or false,
  "confidence": 0.0,
  "reason": "short explanation"
}}
"""

        response = self.llm.simple_completion(prompt)

        try:
            parsed = json.loads(response)
        except Exception:
            parsed = {
                "match": False,
                "confidence": 0.0,
                "reason": "Invalid LLM response"
            }

        parsed["match"] = bool(parsed.get("match", False))
        parsed["confidence"] = float(parsed.get("confidence", 0.0) or 0.0)
        parsed["reason"] = str(parsed.get("reason", "") or "")

        if parsed["confidence"] < self.MIN_CONFIDENCE:
            parsed["match"] = False
            if not parsed["reason"]:
                parsed["reason"] = "Confidence below threshold"

        return parsed