# expected findings: tests.4 (non-test file under tests/ outside
# fixtures/).


def make_user(name="x"):
    return {"name": name, "email": f"{name}@example.com"}
