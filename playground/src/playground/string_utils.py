# expected findings: classes.3/classes.4 (zero-class file with module-level
# functions), classes.5 (module-level constant), docstrings.1 (missing
# docstrings).

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def shout(text):
    return text.upper() + "!"


def whisper(text):
    return text.lower() + "..."


def snake_to_camel(text):
    return "".join(part.title() for part in text.split("_"))
