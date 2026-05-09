import logging
import os
import tempfile

from django.conf import settings

LOGGER = logging.getLogger(__name__)


def _atomic_write(path, content):
    dir_ = os.path.dirname(path)
    os.makedirs(dir_, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_)
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.chmod(tmp, 0o644)
        os.rename(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def sync_extrausers(users):
    """Regenerate /var/lib/extrausers/passwd and group from a queryset of RepositoryUser."""
    path = settings.BORGHIVE.get("EXTRAUSERS_PATH", "/var/lib/extrausers")
    repo_path = settings.BORGHIVE["REPO_PATH"]

    passwd_lines = []
    for u in users:
        home = os.path.join(repo_path, u.name)
        passwd_lines.append(f"{u.name}:x:{u.uid}:{u.group}:Borghive Repo User:{home}:/bin/bash")

    _atomic_write(
        os.path.join(path, "passwd"),
        "\n".join(passwd_lines) + ("\n" if passwd_lines else ""),
    )
    LOGGER.debug("extrausers: wrote %d user(s) to %s/passwd", len(passwd_lines), path)
