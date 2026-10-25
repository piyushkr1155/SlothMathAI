"""Local Ollama AI model service for SlothMate AI."""
import json
import re
from typing import Dict, Any, List, Optional, Tuple
import requests

class OllamaServiceError(Exception):
    """Raised when Ollama connection or generation fails."""
    pass

class ModelNotFoundError(OllamaServiceError):
    """Raised when the requested model is not downloaded in Ollama."""
    pass

class ModelResponseError(OllamaServiceError):
    """Raised when model returns unparseable or schema-violating JSON."""
    pass

class LocalModelService:
    """Service for interacting with local Ollama instances."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:3b",
        timeout: int = 60,
        temperature: float = 0.2
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.temperature = temperature

    # ------------------ Health & Status Checks ------------------

    def get_installed_models(self) -> List[str]:
        """Fetch list of all models currently downloaded in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return [m for m in models if m]
            return []
        except requests.RequestException:
            return []

    def check_status(self) -> Dict[str, Any]:
        """Check Ollama availability and model status.
        
        Returns:
            dict with:
                - state: 'connected' | 'model_missing' | 'unavailable'
                - is_running: bool
                - model_available: bool
                - installed_models: list[str]
                - active_model: str
                - install_command: str
                - message: str
        """
        installed = self.get_installed_models()
        install_cmd = f"ollama pull {self.model_name}"

        # If we could not fetch installed models, Ollama is likely down
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=4)
            is_running = (resp.status_code == 200)
        except requests.RequestException:
            is_running = False

        if not is_running:
            return {
                "state": "unavailable",
                "is_running": False,
                "model_available": False,
                "installed_models": [],
                "active_model": self.model_name,
                "install_command": "ollama serve",
                "message": f"Ollama service is not running at {self.base_url}. Please start Ollama locally.",
            }

        # Check if the configured model is installed (handle tags like ':latest')
        model_installed = False
        target_name = self.model_name.lower()
        for m in installed:
            m_low = m.lower()
            if m_low == target_name:
                model_installed = True
                break
            # E.g. user specified "llama3.2" and ollama reports "llama3.2:latest"
            if m_low.startswith(f"{target_name}:") or target_name.startswith(f"{m_low.split(':')[0]}:"):
                model_installed = True
                break

        if model_installed:
            return {
                "state": "connected",
                "is_running": True,
                "model_available": True,
                "installed_models": installed,
                "active_model": self.model_name,
                "install_command": "",
                "message": f"Local Ollama is connected with model '{self.model_name}'. Ready for offline processing.",
            }
        else:
            return {
                "state": "model_missing",
                "is_running": True,
                "model_available": False,
                "installed_models": installed,
                "active_model": self.model_name,
                "install_command": install_cmd,
                "message": (
                    f"Ollama is running, but model '{self.model_name}' is not downloaded. "
                    f"Run `{install_cmd}` in your terminal to install it."
                ),
            }

    # ------------------ Generation & Structured JSON ------------------

    def generate(self, prompt: str, system: Optional[str] = None, format_json: bool = True) -> str:
        """Call Ollama /api/generate."""
        status = self.check_status()
        if status["state"] == "unavailable":
            raise OllamaServiceError(f"Ollama service unavailable at {self.base_url}. Start Ollama first.")
        if status["state"] == "model_missing":
            raise ModelNotFoundError(
                f"Model '{self.model_name}' is not downloaded. Run: {status['install_command']}"
            )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            }
        }
        if system:
            payload["system"] = system
        if format_json:
            payload["format"] = "json"

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            if resp.status_code != 200:
                raise OllamaServiceError(
                    f"Ollama returned HTTP error {resp.status_code}: {resp.text}"
                )
            data = resp.json()
            return data.get("response", "")
        except requests.Timeout:
            raise OllamaServiceError(
                f"Ollama request timed out after {self.timeout} seconds. The local model may be overloaded."
            )
        except requests.RequestException as e:
            raise OllamaServiceError(f"Error communicating with local Ollama: {str(e)}")

    def generate_structured(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """Generate and parse structured JSON with bounded repair."""
        raw_text = self.generate(prompt=prompt, system=system, format_json=True)
        
        parsed = self._repair_and_parse_json(raw_text)
        if parsed is not None:
            return parsed

        # If initial parse failed and retries allowed, ask model to repair
        if max_retries > 0:
            repair_prompt = (
                f"The following JSON response was malformed:\n\n{raw_text}\n\n"
                "Fix it and return ONLY valid, well-formed JSON without commentary:"
            )
            retry_text = self.generate(prompt=repair_prompt, system=system, format_json=True)
            repaired = self._repair_and_parse_json(retry_text)
            if repaired is not None:
                return repaired

        raise ModelResponseError(
            f"Failed to parse valid JSON from local model response.\nRaw response excerpt: {raw_text[:300]}..."
        )

    # ------------------ JSON Repair Utilities ------------------

    @staticmethod
    def _repair_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
        """Attempt to extract and parse valid JSON from text."""
        if not text or not text.strip():
            return None

        clean = text.strip()

        # 1. Direct parse attempt
        try:
            obj = json.loads(clean)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

        # 2. Strip markdown fences: ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
        if fence_match:
            try:
                obj = json.loads(fence_match.group(1).strip())
                if isinstance(obj, dict):
                    return obj
            except Exception:
                pass

        # 3. Find outer braces: { ... }
        brace_match = re.search(r"(\{[\s\S]*\})", clean)
        if brace_match:
            candidate = brace_match.group(1).strip()
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                # 4. Try removing trailing commas: , ] or , }
                subbed = re.sub(r",\s*([\]\}])", r"\1", candidate)
                try:
                    obj = json.loads(subbed)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    pass

        return None
