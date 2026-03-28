"""
Multi-Provider LLM System - Free API Priority Chain.

Priority order:
1. Google Gemini (free tier - 15 RPM, 1M tokens/day)
2. Groq (free tier - Llama 3, very fast)
3. OpenAI (paid, if key available)
4. Local structured fallback (no API needed)

Each provider generates cricket match analysis with consistent output format.
"""

import json
import os
import re
import time
from abc import ABC, abstractmethod

import requests

from utils.logger import logger
from config.settings import settings


class RateLimitTracker:
    """Track rate limits per provider to avoid hitting them repeatedly."""

    def __init__(self):
        self._cooldowns = {}  # provider_name -> (cooldown_until, consecutive_failures)

    def mark_rate_limited(self, provider_name: str, retry_after: int = 60):
        """Mark a provider as rate-limited."""
        failures = self._cooldowns.get(provider_name, (0, 0))[1] + 1
        # Exponential backoff: 60s, 120s, 240s, max 600s
        wait = min(retry_after * (2 ** (failures - 1)), 600)
        self._cooldowns[provider_name] = (time.time() + wait, failures)
        logger.warning(f"LLM: {provider_name} rate-limited, cooldown {wait}s (failure #{failures})")

    def is_cooled_down(self, provider_name: str) -> bool:
        """Check if provider has cooled down from rate limit."""
        if provider_name not in self._cooldowns:
            return True
        cooldown_until, _ = self._cooldowns[provider_name]
        if time.time() >= cooldown_until:
            # Reset failures on successful cooldown
            self._cooldowns.pop(provider_name, None)
            return True
        return False

    def clear(self, provider_name: str):
        """Clear rate limit for a provider after successful call."""
        self._cooldowns.pop(provider_name, None)


_rate_tracker = RateLimitTracker()


def _is_rate_limit_error(error) -> bool:
    """Detect if an error is a rate limit (429) or quota exceeded."""
    err_str = str(error).lower()
    return any(k in err_str for k in ["429", "rate limit", "quota", "too many requests", "resource exhausted"])


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generate text from prompt."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini - Free tier (15 RPM, 1M tokens/day)."""

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")

    @property
    def name(self) -> str:
        return "Google Gemini 2.0 Flash"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        try:
            resp = requests.post(
                f"{self.API_URL}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                        "topP": 0.95,
                    },
                },
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}")
            raise


class GroqProvider(LLMProvider):
    """Groq - Free tier (Llama 3.3 70B, very fast inference)."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")

    @property
    def name(self) -> str:
        return "Groq Llama 3.3 70B"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        try:
            resp = requests.post(
                self.API_URL,
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": "You are an expert IPL cricket analyst with deep knowledge of T20 cricket, player statistics, team strategies, and match conditions. Provide detailed, data-driven analysis."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"Groq API failed: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4o-mini (paid)."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self):
        self.api_key = settings.openai_api_key or ""

    @property
    def name(self) -> str:
        return "OpenAI GPT-4o-mini"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        try:
            resp = requests.post(
                self.API_URL,
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert IPL cricket analyst with deep knowledge of T20 cricket, player statistics, team strategies, and match conditions. Provide detailed, data-driven analysis."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI API failed: {e}")
            raise


class LocalFallbackProvider(LLMProvider):
    """Structured text generation without any API - always available."""

    @property
    def name(self) -> str:
        return "Local Structured Analysis"

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        # Extract key data from prompt to build structured analysis
        return self._build_structured_analysis(prompt)

    def _build_structured_analysis(self, prompt: str) -> str:
        """Build a structured analysis from the context in the prompt."""
        lines = prompt.split("\n")
        analysis_parts = []

        # Extract teams
        teams = []
        winner = ""
        confidence = ""
        venue = ""
        weather_info = ""
        toss_info = ""
        key_factors = []

        for line in lines:
            line_lower = line.lower().strip()
            if "team1:" in line_lower or "team 1:" in line_lower:
                teams.append(line.split(":", 1)[-1].strip())
            elif "team2:" in line_lower or "team 2:" in line_lower:
                teams.append(line.split(":", 1)[-1].strip())
            elif "predicted winner:" in line_lower:
                winner = line.split(":", 1)[-1].strip()
            elif "confidence:" in line_lower:
                confidence = line.split(":", 1)[-1].strip()
            elif "venue:" in line_lower:
                venue = line.split(":", 1)[-1].strip()
            elif "weather:" in line_lower or "condition:" in line_lower:
                weather_info = line.split(":", 1)[-1].strip()
            elif "toss:" in line_lower:
                toss_info = line.split(":", 1)[-1].strip()
            elif "factor" in line_lower or "advantage" in line_lower:
                key_factors.append(line.strip())

        t1 = teams[0] if len(teams) > 0 else "Team 1"
        t2 = teams[1] if len(teams) > 1 else "Team 2"

        analysis = f"""MATCH ANALYSIS: {t1} vs {t2}

PREDICTION: {winner or t1} is predicted to win this encounter with {confidence or 'moderate'} confidence.

VENUE ANALYSIS: {venue or 'The venue'} will play a crucial role in this match. The conditions will test both teams' adaptability.

{'WEATHER: ' + weather_info + '. This will influence the toss decision and team strategy.' if weather_info else ''}

{'TOSS STRATEGY: ' + toss_info if toss_info else ''}

KEY MATCHUPS: The contest between the top-order batsmen and new-ball bowlers will be decisive. The team that handles the middle overs better will likely come out on top.

VERDICT: This promises to be a closely fought encounter. {winner or t1} holds a slight edge based on current form, squad strength, and historical performance at this venue. However, the impact player rule adds an extra tactical dimension that could swing the match either way.

Note: This is a structured analysis. Set up a free Gemini or Groq API key for AI-powered detailed insights."""

        return analysis


class LLMChain:
    """
    Multi-provider LLM chain with automatic failover and rate limit detection.

    Tries providers in priority order:
    1. Gemini (free) → 2. Groq (free) → 3. OpenAI (paid) → 4. Local fallback

    Rate limit handling:
    - Detects 429/quota errors automatically
    - Exponential backoff per provider (60s → 120s → 240s → 600s max)
    - Skips rate-limited providers until cooldown expires
    - Logs every failover so you can monitor usage
    """

    def __init__(self):
        self.providers = [
            GeminiProvider(),
            GroqProvider(),
            OpenAIProvider(),
            LocalFallbackProvider(),
        ]
        self._active_provider = None
        self._call_count = 0
        self._failover_log = []
        self._detect_provider()

    def _detect_provider(self):
        """Find the first available provider."""
        for provider in self.providers:
            if provider.is_available():
                self._active_provider = provider
                logger.info(f"LLM Provider: {provider.name}")
                return
        self._active_provider = self.providers[-1]

    @property
    def active_provider_name(self) -> str:
        return self._active_provider.name if self._active_provider else "None"

    def get_failover_status(self) -> dict:
        """Get current failover status for monitoring."""
        return {
            "active_provider": self.active_provider_name,
            "total_calls": self._call_count,
            "recent_failovers": self._failover_log[-10:],
            "provider_status": {
                p.name: {
                    "available": p.is_available(),
                    "cooled_down": _rate_tracker.is_cooled_down(p.name),
                }
                for p in self.providers
            },
        }

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generate text using the provider chain with automatic failover."""
        self._call_count += 1

        for provider in self.providers:
            if not provider.is_available():
                continue
            # Skip providers still in cooldown from rate limit
            if not _rate_tracker.is_cooled_down(provider.name):
                logger.info(f"LLM: Skipping {provider.name} (rate-limited, cooling down)")
                continue
            try:
                result = provider.generate(prompt, max_tokens, temperature)
                if result:
                    _rate_tracker.clear(provider.name)
                    return result
            except Exception as e:
                if _is_rate_limit_error(e):
                    _rate_tracker.mark_rate_limited(provider.name)
                    self._failover_log.append({
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "from": provider.name,
                        "reason": "rate_limit",
                    })
                else:
                    logger.warning(f"{provider.name} failed: {e}")
                    self._failover_log.append({
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "from": provider.name,
                        "reason": str(e)[:100],
                    })
                continue

        # Ultimate fallback
        return LocalFallbackProvider().generate(prompt, max_tokens, temperature)

    def generate_match_analysis(self, match_context: dict) -> str:
        """Generate a detailed match analysis from structured match data."""
        prompt = self._build_match_prompt(match_context)
        return self.generate(prompt, max_tokens=1200, temperature=0.7)

    def generate_agent_reasoning(self, agent_name: str, task: str, context: dict) -> str:
        """Generate reasoning for a specific agent's analysis."""
        prompt = f"""You are the {agent_name} in an IPL cricket prediction system.

YOUR TASK: {task}

MATCH CONTEXT:
{json.dumps(context, indent=2, default=str)}

Provide your expert analysis in 150-200 words. Be specific with numbers, player names, and data-driven insights. Focus on actionable conclusions, not generic statements."""

        return self.generate(prompt, max_tokens=500, temperature=0.6)

    def generate_debate(self, predictions: dict, agent_analyses: list[dict]) -> str:
        """Generate a debate between different prediction perspectives."""
        prompt = f"""You are moderating a debate between IPL cricket prediction agents.

AGENT PREDICTIONS:
{json.dumps(agent_analyses, indent=2, default=str)}

ENSEMBLE PREDICTION:
{json.dumps(predictions, indent=2, default=str)}

Simulate a brief debate (200 words) where:
1. The BULL case agent argues why the predicted winner will win convincingly
2. The BEAR case agent argues why the underdog could upset
3. The MODERATOR synthesizes both views into a final verdict

Be specific with player matchups, venue factors, and statistical evidence."""

        return self.generate(prompt, max_tokens=600, temperature=0.8)

    def _build_match_prompt(self, ctx: dict) -> str:
        """Build a comprehensive match analysis prompt."""
        return f"""Analyze this IPL 2026 match and provide a detailed prediction report.

MATCH: {ctx.get('team1', 'Team 1')} vs {ctx.get('team2', 'Team 2')}
VENUE: {ctx.get('venue', 'TBD')}, {ctx.get('city', '')}
DATE: {ctx.get('date', 'TBD')} | TIME: {ctx.get('time_ist', '19:30')} IST
MATCH NUMBER: {ctx.get('match_number', '?')}

TEAM 1 ({ctx.get('team1', '')}):
- Captain: {ctx.get('team1_captain', 'Unknown')}
- Playing XI: {', '.join(ctx.get('team1_xi', [])) or 'Not announced'}
- Squad Strength: {json.dumps(ctx.get('team1_strength', {}), default=str)}

TEAM 2 ({ctx.get('team2', '')}):
- Captain: {ctx.get('team2_captain', 'Unknown')}
- Playing XI: {', '.join(ctx.get('team2_xi', [])) or 'Not announced'}
- Squad Strength: {json.dumps(ctx.get('team2_strength', {}), default=str)}

WEATHER: {json.dumps(ctx.get('weather', {}), default=str)}

TOSS PREDICTION: {json.dumps(ctx.get('toss_prediction', {}), default=str)}

RAIN ANALYSIS: {json.dumps(ctx.get('rain_analysis', {}), default=str)}

IMPACT PLAYER: {json.dumps(ctx.get('impact_player', {}), default=str)}

MODEL PREDICTIONS:
- Ensemble Win Probability: {ctx.get('team1', '')} {ctx.get('team1_prob', 50)}% vs {ctx.get('team2', '')} {ctx.get('team2_prob', 50)}%
- Predicted Winner: {ctx.get('predicted_winner', 'TBD')}
- Confidence: {ctx.get('confidence', 0)}%
- Key Factors: {json.dumps(ctx.get('key_factors', []), default=str)}

NEWS & SENTIMENT: {json.dumps(ctx.get('news_sentiment', {}), default=str)}

FORM & MOMENTUM: {json.dumps(ctx.get('form_data', {}), default=str)}

HEAD TO HEAD: {json.dumps(ctx.get('h2h', {}), default=str)}

Write a 400-500 word expert analysis covering:
1. Match Overview & Context
2. Key Player Matchups to Watch
3. Venue & Conditions Impact
4. Tactical Breakdown (toss, batting order, impact player strategy)
5. Risk Factors (rain, injuries, form slumps)
6. Final Verdict with confidence level

Use specific stats and player names. Be bold with your predictions, not generic."""
