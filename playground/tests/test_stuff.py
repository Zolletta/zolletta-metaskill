# expected findings: tests.2 (two Test* classes in one file),
# tests.3 (test names without three segments), tests.5 (no
# '# --- section ---' comments).
from playground.src.playground.string_utils import shout, whisper


class TestThings:
    def test_x(self):
        assert shout("hi") == "HI!"

    def testItWorks(self):
        assert whisper("HI") == "hi..."


class TestOtherThings:
    def test_y(self):
        assert True

    def test2(self):
        assert 1 + 1 == 2
