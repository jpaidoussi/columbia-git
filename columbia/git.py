"""Abstract handling of git repositories."""

import hashlib
import os
import shutil
import subprocess
import urllib


class RepositoryLocation:
    def __init__(self, working_directory, repository_url):
        self.working_directory = working_directory
        self.url = repository_url
        self.repository_url = urllib.parse.urlparse(repository_url)
        self.url_hash = hashlib.md5(self.url.encode("utf-8")).hexdigest()
        self.parent_directory = self.url_hash[:2]
        self.repository_directory = self.url_hash[2:]
        self.path = os.path.join(
            self.working_directory,
            self.parent_directory,
            self.repository_directory
        )

    @property
    def exists(self):
        return os.path.exists(self.path)

    def create(self):
        os.makedirs(self.path, exist_ok=True)

    def remove(self):
        shutil.rmtree(self.path)
        # Check if the parent is now empty and remove it.
        parent = os.path.join(self.working_directory, self.parent_directory)
        if not os.listdir(parent):
            shutil.rmtree(parent)

    def fq_path(self, relative_path):
        return os.path.join(self.path, relative_path)

    def path_exists(self, relative_path):
        return os.path.exists(self.fq_path(relative_path))


class GitError(Exception):
    """A generic container for errors generated by the git command."""


class Repository:
    def __init__(self, repository_location, binary):
        self._url = repository_location.url
        self.location = repository_location
        self.binary = binary

        # Clone the repo on initialization. NOTE: the properties
        # accessed by the methods below need to be defined before calling
        # the methods.
        if not self.ready:
            self._ready_target_location()
            self._clone()

    @property
    def ready(self):
        if not self.location.exists:
            return False

        if not self.location.path_exists(".git"):
            return False

        return True

    def _git(self, command, arguments=[]):
        args = [self.binary, command]
        args.extend(arguments)
        result = subprocess.run(
            args=args, cwd=self.location.path, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True, check=True
        )
        return result

    def _ready_target_location(self):
        self.location.create()

    def _remove_target_location(self):
        self.location.remove()

    def _hard_reset(self):
        self._git("reset", ["--hard", "HEAD"])

    def _clone(self):
        try:
            self._git("clone", [self._url, self.location.path])
        except subprocess.CalledProcessError as exc:
            message = exc.stderr
            # Clone failed, so cleanup the directories.
            self.location.remove()
            raise GitError(message)

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
        result = self._git("rev-parse", ["--verify", "head"])
        return result.stdout.strip()

    def branches(self):
        result = self._git("branch", ["-a"])
        branches = result.stdout.strip().split("\n")
        branches = [b.strip() for b in branches]
        return branches

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


def setup_repository(working_directory, url, binary="/usr/bin/git"):
    """A helper function to construct a Repository with a RepositoryLocation.
    """
    location = RepositoryLocation(working_directory, url)
    return Repository(location, binary)
