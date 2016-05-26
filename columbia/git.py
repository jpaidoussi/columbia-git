"""Abstract handling of git repositories."""

# Python 2 compatability imports
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import hashlib
import os

import shutil
import subprocess


def repo_url_hash_path_builder(working_directory, url):
    """Get a unique repo path in the given working_directory based on a two
    level hash of the repo URL.
    """
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    parent_directory = url_hash[:2]
    repository_directory = url_hash[2:]
    return Path(working_directory)\
        .joinpath(parent_directory)\
        .joinpath(repository_directory)


class RepositoryLocation:
    def __init__(
            self, working_directory, repository_url,
            path_builder_func=repo_url_hash_path_builder):
        self.working_directory = working_directory
        self.url = repository_url
        self.repository_url = urlparse(repository_url)
        self.path = path_builder_func(working_directory, repository_url)

    @property
    def exists(self):
        return self.path.exists()

    def create(self):
        if self.exists:
            return False

        self.path.mkdir(parents=True, exist_ok=True)
        return True

    def remove(self):
        shutil.rmtree(str(self.path))
        # Remove the parent directory if empty.
        try:
            self.path.parent.rmdir()
        except OSError:
            # Parent directory isn't empty, do nothing.
            pass

    def fq_path(self, relative_path):
        return self.path / relative_path

    def path_exists(self, relative_path):
        return self.fq_path(relative_path).exists()

    def search(self, pattern):
        return self.path.glob(pattern)


class RepositoryError(Exception):
    """A generic container for errors generated by the git command."""


class Repository:
    def __init__(self, repository_location, binary, bare=False, clone=False):
        self._url = repository_location.url
        self.location = repository_location
        self.binary = binary
        self.bare = bare
        self.created = False

        # Clone the repo on initialization. NOTE: the properties
        # accessed by the methods below need to be defined before calling
        # the methods.
        if not self.ready and clone:
            self._ready_target_location()
            self._clone(self.bare)

    @property
    def ready(self):
        if not self.location.exists:
            return False

        if self.bare:
            try:
                self._git("rev-parse", ["--git-dir"])
            except subprocess.CalledProcessError:
                return False

            return True
        else:
            if not self.location.path_exists(".git"):
                return False

        return True

    def _git(self, command, arguments=None):
        if arguments is None:
            arguments = []
        args = [self.binary, command]
        args.extend(arguments)
        result = subprocess.check_output(
            args=args, cwd=str(self.location.path), universal_newlines=True
        )
        return result

    def _ready_target_location(self):
        self.created = self.location.create()

    def _remove_target_location(self):
        self.location.remove()

    def _hard_reset(self):
        self._git("reset", ["--hard", "HEAD"])

    def _clone(self, bare):
        try:
            args = [self._url, str(self.location.path)]
            if bare:
                args.insert(0, "--bare")
            self._git("clone", args)
        except subprocess.CalledProcessError as exc:
            message = exc.stderr
            # Clone failed, so cleanup the directories, but only if we created
            # the diretory for the clone attempt.
            if self.created:
                self.location.remove()
            raise RepositoryError(message)

    def _checkout(self, reference):
        self._git("checkout", [reference])

    def _pull(self):
        self._git("pull")

    def update_to(self, reference):
        """Make a given reference active.

        This is equivalent to a checkout and pull on the given reference.

        The reference can be any git reference (commit, branch, tag, ...).
        """
        self._checkout(reference)
        self._pull()

    def export(self, destination):
        """Export all the files of the current working copy to the given
        destination.

        This will ensure that none of the git specific files are copied to
        the target destination.
        """
        # Ensure trailing slash is present.
        destination = os.path.join(destination, "")
        self._git(
            "checkout-index",
            ["-a", "-f", "--prefix={0}".format(destination)]
        )

    def latest_commit(self):
        result = self._git("rev-parse", ["--verify", "HEAD"])
        return result.strip()

    def branches(self):
        result = self._git("ls-remote", ["--heads"])
        if not result:
            return []

        branches = result.strip().split("\n")
        branches = [b.split("refs/heads/")[1] for b in branches]
        return branches

    @property
    def active_branch(self):
        result = self._git("symbolic-ref", ["HEAD"])
        if not result:
            return None

        branch = result.strip()
        return branch.split("refs/heads/")[1]

    def tags(self):
        result = self._git("ls-remote", ["--tags"])
        if not result:
            return []

        tags = result.strip().split("\n")
        tags = [t.split("refs/tags/")[1] for t in tags]
        return tags

    def clean(self, thorough=False):
        """Cleans the current working copy of the repository.

        If thorough is specified this method complete moves the directory
        of the working copy. Otherwise it just performs a hard git
        reset to HEAD.
        """
        if thorough:
            self._remove_target_location()
        else:
            self._hard_reset()

    def fq_path(self, relative_path):
        """Returns a fully qualified path given a path relative to the
        repository root.
        """
        return self.location.fq_path(relative_path)

    def search(self, pattern):
        """Returns a list of file paths matching the given pattern."""
        return self.location.search(pattern)


def setup_repository(working_directory, url, binary="/usr/bin/git", bare=False):
    """A helper function to construct a Repository with a RepositoryLocation.
    """
    location = RepositoryLocation(working_directory, url)
    return Repository(location, binary, bare)
