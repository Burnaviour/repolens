import os
import sys

import pytest

from repolens.scanner import detect_language, scan_repository


def paths(root, **kwargs):
    return [f.path for f in scan_repository(root, **kwargs)]


def test_finds_known_languages_and_skips_unknown(make_repo):
    root = make_repo({"a.py": "", "b.ts": "", "Dockerfile": "", "image.png": "", "notes.xyz": ""})
    assert paths(root) == ["Dockerfile", "a.py", "b.ts"]


def test_respects_root_and_nested_gitignore(make_repo):
    root = make_repo(
        {
            ".gitignore": "*.log\ngenerated/\n",
            "app.py": "",
            "debug.log.py": "",
            "generated/x.py": "",
            "pkg/.gitignore": "local_*.py\n!local_keep.py\n",
            "pkg/local_tmp.py": "",
            "pkg/local_keep.py": "",
            "pkg/real.py": "",
            "other/local_tmp.py": "",
        }
    )
    assert paths(root) == [
        "app.py",
        "debug.log.py",
        "other/local_tmp.py",  # pkg/.gitignore does not apply outside pkg/
        "pkg/local_keep.py",
        "pkg/real.py",
    ]


def test_deeper_gitignore_can_reinclude(make_repo):
    root = make_repo({".gitignore": "*.json\n", "keep/.gitignore": "!*.json\n", "keep/a.json": ""})
    assert paths(root) == ["keep/a.json"]


def test_skips_hidden_virtualenvs_and_build_dirs(make_repo):
    root = make_repo(
        {
            "main.py": "",
            ".hidden/x.py": "",
            "node_modules/lib/index.js": "",
            "__pycache__/main.py": "",
            "myenv/pyvenv.cfg": "",
            "myenv/lib/site.py": "",
            "pkg.egg-info/x.py": "",
        }
    )
    assert paths(root) == ["main.py"]


def test_extra_exclude_patterns(make_repo):
    root = make_repo({"a.py": "", "tests/test_a.py": "", "docs/conf.py": ""})
    assert paths(root, exclude=["tests/", "conf.py"]) == ["a.py"]


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_does_not_follow_symlinks(make_repo, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.py").write_text("")
    root = make_repo({"a.py": ""})
    os.symlink(outside, root / "linked_dir")
    os.symlink(outside / "secret.py", root / "linked.py")
    assert paths(root) == ["a.py"]


def test_detect_language():
    assert detect_language("x.PY") == "python"
    assert detect_language("Makefile") == "makefile"
    assert detect_language("x.unknown") is None
