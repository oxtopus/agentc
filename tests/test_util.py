import os
import sys

import pytest

from agentc.util import copy_tracked_tree, hash_dir, iter_tracked_files, slugify


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


def _build_skill_with_cruft(src):
    (src / "SKILL.md").write_text("# skill\n")
    (src / ".env").write_text("SECRET=1\n")
    (src / ".DS_Store").write_text("x")
    git = src / ".git"
    git.mkdir()
    (git / "config").write_text("[core]\n")
    pyc_dir = src / "__pycache__"
    pyc_dir.mkdir()
    (pyc_dir / "x.pyc").write_text("bytes")


def test_copy_tracked_tree_skips_cruft(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _build_skill_with_cruft(src)
    dst = tmp_path / "dst"
    copy_tracked_tree(src, dst)

    assert (dst / "SKILL.md").is_file()
    # .env is copied (not in skip list); plan minimum required to block .git/cache/.DS_Store
    assert not (dst / ".git").exists()
    assert not (dst / "__pycache__").exists()
    assert not (dst / ".DS_Store").exists()


def test_copy_tracked_tree_matches_hash_enumeration(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    _build_skill_with_cruft(src)
    (src / "nested").mkdir()
    (src / "nested" / "a.md").write_text("a")
    dst = tmp_path / "dst"
    copy_tracked_tree(src, dst)

    src_rel = sorted(f.relative_to(src) for f in iter_tracked_files(src))
    dst_rel = sorted(f.relative_to(dst) for f in iter_tracked_files(dst))
    assert src_rel == dst_rel


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require admin on win")
def test_copy_tracked_tree_skips_symlinks(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "SKILL.md").write_text("# skill\n")
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    os.symlink(outside, src / "leak.txt")

    dst = tmp_path / "dst"
    copy_tracked_tree(src, dst)
    assert (dst / "SKILL.md").is_file()
    assert not (dst / "leak.txt").exists()
