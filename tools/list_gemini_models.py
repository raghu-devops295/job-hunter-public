"""
Lists the Gemini models YOUR key can use (they change over time).

Run:   py tools\\list_gemini_models.py

Pick one with "flash" in the name (fast + free-tier friendly), then set it:
    setx GEMINI_MODEL "the-model-name"
and open a NEW black window.
"""

import os

import requests

key = os.environ.get("GEMINI_API_KEY")
if not key:
    raise SystemExit("GEMINI_API_KEY is not set. See the setup steps.")

r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                 headers={"x-goog-api-key": key}, timeout=30)
r.raise_for_status()
for m in r.json().get("models", []):
    if "generateContent" in m.get("supportedGenerationMethods", []):
        print(m["name"].replace("models/", ""))
