# Deliberately clean mirror test so tests.1 flags only the unmirrorred
# sources (user_manager.py, report_engine.py, notification_service.py).
from playground.src.playground.string_utils import shout, snake_to_camel, whisper


class TestStringUtils:
    # --- shouting ---

    def test_shout_uppercases_text(self):
        assert shout("hey") == "HEY!"

    def test_whisper_lowercases_text(self):
        assert whisper("HEY") == "hey..."

    def test_snake_to_camel_joins_parts(self):
        assert snake_to_camel("foo_bar") == "FooBar"
