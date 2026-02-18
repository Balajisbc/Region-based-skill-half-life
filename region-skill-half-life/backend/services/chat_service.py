"""Service boundary for AI assistant orchestration and context routing."""

from __future__ import annotations

import json
import importlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterator

from config import get_settings


@dataclass
class ConversationTurn:
	"""Conversation turn in chat memory."""

	role: str
	content: str
	timestamp: str


@dataclass
class RegionContext:
	"""Selected region and skill context for the assistant."""

	country: str
	city: str
	skill: str


class ConversationMemoryStore:
	"""Thread-safe in-memory conversation store keyed by session id."""

	def __init__(self, max_turns_per_session: int = 30) -> None:
		self.max_turns_per_session = max_turns_per_session
		self._history: dict[str, list[ConversationTurn]] = {}
		self._contexts: dict[str, RegionContext] = {}
		self._lock = RLock()

	def set_context(self, session_id: str, context: RegionContext) -> None:
		with self._lock:
			self._contexts[session_id] = context

	def get_context(self, session_id: str) -> RegionContext | None:
		with self._lock:
			return self._contexts.get(session_id)

	def append_turn(self, session_id: str, role: str, content: str) -> None:
		with self._lock:
			turns = self._history.setdefault(session_id, [])
			turns.append(
				ConversationTurn(
					role=role,
					content=content,
					timestamp=datetime.now(timezone.utc).isoformat(),
				)
			)
			if len(turns) > self.max_turns_per_session:
				del turns[: len(turns) - self.max_turns_per_session]

	def history(self, session_id: str) -> list[ConversationTurn]:
		with self._lock:
			return list(self._history.get(session_id, []))


class ChatServiceError(ValueError):
	"""Raised for invalid chat service inputs and execution failures."""


_memory = ConversationMemoryStore()


def _has_real_openai_key() -> bool:
	"""Return whether a non-placeholder OpenAI key is configured."""
	settings = get_settings()
	key = settings.openai_api_key.strip()
	if not key or not key.startswith("sk-"):
		return False
	placeholder_markers = (
		"replace-with-valid-openai-key",
		"replace",
		"example",
	)
	return not any(marker in key.lower() for marker in placeholder_markers)


def _build_system_prompt(context: RegionContext) -> str:
	"""Build region-aware system prompt with strict structured output format."""
	return (
		"You are a region-aware workforce intelligence assistant. "
		f"Current context: country={context.country}, city={context.city}, skill={context.skill}. "
		"Answer with concise, evidence-oriented reasoning and return JSON only with keys: "
		"summary, regional_signals, implications, action_plan, risk_notes, follow_up_questions."
	)


def _history_to_messages(turns: list[ConversationTurn], limit: int = 12) -> list[dict[str, str]]:
	"""Convert conversation turns to LLM chat message format."""
	selected = turns[-limit:]
	return [{"role": turn.role, "content": turn.content} for turn in selected]


def _parse_or_wrap_structured_response(text: str) -> dict[str, Any]:
	"""Parse model JSON output or safely wrap plain text into structured schema."""
	try:
		parsed = json.loads(text)
		if isinstance(parsed, dict):
			return {
				"summary": str(parsed.get("summary", "")),
				"regional_signals": list(parsed.get("regional_signals", [])),
				"implications": list(parsed.get("implications", [])),
				"action_plan": list(parsed.get("action_plan", [])),
				"risk_notes": list(parsed.get("risk_notes", [])),
				"follow_up_questions": list(parsed.get("follow_up_questions", [])),
			}
	except json.JSONDecodeError:
		pass

	return {
		"summary": text.strip(),
		"regional_signals": [],
		"implications": [],
		"action_plan": [],
		"risk_notes": [],
		"follow_up_questions": [],
	}


def _rule_based_structured_explanation(
	user_message: str,
	context: RegionContext,
	history: list[ConversationTurn],
) -> dict[str, Any]:
	"""Generate contextual structured explanation using deterministic rules."""
	message = user_message.lower()

	regional_signals = [
		f"Market context anchored to {context.city}, {context.country} for {context.skill}.",
		"Historical demand volatility and competition dynamics should guide transition timing.",
	]

	implications: list[str] = []
	if "salary" in message or "pay" in message:
		implications.append("Salary outcomes depend on local demand elasticity and competition intensity.")
	if "risk" in message:
		implications.append("Risk increases when demand decay accelerates while automation pressure rises.")
	if "pivot" in message or "switch" in message:
		implications.append("Pivot feasibility improves when adjacent skills have strong local demand and lower saturation.")
	if not implications:
		implications.append("Decision quality improves by combining demand trend, volatility, and skill saturation signals.")

	action_plan = [
		"Validate current regional demand and competition for the selected skill.",
		"Prioritize adjacent high-demand skills with lower automation exposure.",
		"Build a 90-day upskilling plan and reassess analytics monthly.",
	]

	risk_notes = [
		"Treat rapidly increasing competition as an early warning for salary compression.",
		"Track volatility shifts before committing to long-term specialization.",
	]

	follow_up_questions = [
		"Should I compare this city with nearby alternatives for the same skill?",
		"Do you want a safe, moderate, or aggressive pivot path from this skill?",
	]

	history_hint = "" if not history else " Conversation history was considered for continuity."
	summary = (
		f"For {context.skill} in {context.city}, {context.country}, the recommended next step is to align skill growth "
		"with local demand resilience and automation exposure." + history_hint
	)

	return {
		"summary": summary,
		"regional_signals": regional_signals,
		"implications": implications,
		"action_plan": action_plan,
		"risk_notes": risk_notes,
		"follow_up_questions": follow_up_questions,
	}


def _stream_openai_structured_response(
	messages: list[dict[str, str]],
) -> Iterator[str]:
	"""Yield streaming text chunks from OpenAI chat completion."""
	openai_module = importlib.import_module("openai")
	openai_client_class = getattr(openai_module, "OpenAI")
	client = openai_client_class(api_key=get_settings().openai_api_key)
	stream = client.chat.completions.create(
		model="gpt-4o-mini",
		messages=messages,
		temperature=0.2,
		stream=True,
	)

	for chunk in stream:
		delta = chunk.choices[0].delta.content if chunk.choices else None
		if delta:
			yield delta


def stream_region_aware_assistant(
	session_id: str,
	message: str,
	country: str,
	city: str,
	skill: str,
) -> Iterator[dict[str, Any]]:
	"""Stream assistant response events with region and skill context awareness.

	Emits events:
	- {"type": "start", ...}
	- {"type": "chunk", "content": "..."} (OpenAI mode)
	- {"type": "final", "response": {...}}
	"""
	if not session_id.strip():
		raise ChatServiceError("session_id is required.")
	if not message.strip():
		raise ChatServiceError("message is required.")

	context = RegionContext(country=country.strip(), city=city.strip(), skill=skill.strip())
	_memory.set_context(session_id, context)
	_memory.append_turn(session_id, role="user", content=message.strip())
	history = _memory.history(session_id)

	use_openai = _has_real_openai_key()
	mode = "openai_streaming" if use_openai else "rule_based"
	yield {"type": "start", "mode": mode, "session_id": session_id, "context": asdict(context)}

	assistant_text = ""
	if use_openai:
		messages = [{"role": "system", "content": _build_system_prompt(context)}] + _history_to_messages(history)
		try:
			for token in _stream_openai_structured_response(messages):
				assistant_text += token
				yield {"type": "chunk", "content": token}
		except Exception:
			mode = "rule_based"
			structured = _rule_based_structured_explanation(message, context, history)
			assistant_text = json.dumps(structured, ensure_ascii=False)
	else:
		structured = _rule_based_structured_explanation(message, context, history)
		assistant_text = json.dumps(structured, ensure_ascii=False)

	_memory.append_turn(session_id, role="assistant", content=assistant_text)
	final_history = [asdict(turn) for turn in _memory.history(session_id)]
	structured_response = _parse_or_wrap_structured_response(assistant_text)

	yield {
		"type": "final",
		"response": {
			"mode": mode,
			"session_id": session_id,
			"context": asdict(context),
			"structured_explanation": structured_response,
			"conversation_history": final_history,
		},
	}


def get_region_aware_assistant_response(
	session_id: str,
	message: str,
	country: str,
	city: str,
	skill: str,
) -> dict[str, Any]:
	"""Return the final structured assistant response in non-streaming form."""
	final_event: dict[str, Any] | None = None
	for event in stream_region_aware_assistant(
		session_id=session_id,
		message=message,
		country=country,
		city=city,
		skill=skill,
	):
		if event.get("type") == "final":
			final_event = event

	if final_event is None:
		raise ChatServiceError("Failed to generate assistant response.")

	return dict(final_event["response"])


def get_conversation_history(session_id: str) -> list[dict[str, str]]:
	"""Return session conversation history for UI restoration and traceability."""
	return [asdict(turn) for turn in _memory.history(session_id)]
