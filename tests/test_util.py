from agentc.util import hash_dir, slugify


def test_slugify_lowercases():
    assert slugify("FooBar") == "foobar"


def test_slugify_replaces_spaces():
    assert slugify("foo bar") == "foo-bar"


def test_slugify_fallback():
    assert slugify("---") == "agent"


def test_hash_dir_stable(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    assert hash_dir(tmp_path) == hash_dir(tmp_path)


def test_hash_dir_changes_on_content(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    first = hash_dir(tmp_path)
    (tmp_path / "a.txt").write_text("HELLO")
    assert hash_dir(tmp_path) != first
