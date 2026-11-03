"""Test setup: supply placeholder settings."""

import os

# Required settings that the app needs but that tests should not need real values for
_SETTINGS_PLACEHOLDERS = {
    "API_HASH": "test-api-hash",
    "API_ID": "0",
    "MY_USERNAME": "@test",
    "OPENAI_API_KEY": "test-openai-api-key",
}

for _name, _value in _SETTINGS_PLACEHOLDERS.items():
    os.environ.setdefault(_name, _value)
