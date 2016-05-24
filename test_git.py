import pytest
import shutil
import tempfile

from columbia import git


@pytest.fixture(scope="module")
def tempdirectory():
    testdir = tempfile.mkdtemp()

    def fin():
        shutil.rmtree(testdir)

    return testdir


@pytest.fixture(scope="module")
def repo(tempdirectory):
    repo = git.setup_repository(
        tempdirectory,
        "https://github.com/jpaidoussi/columbia-git.git",
        binary="/usr/local/bin/git"
    )
    return repo


def test_repository_ready(repo):
    assert repo.ready is True


def test_repository_branches(repo):
    assert repo.branches() == ["master"]
