import os
import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

import borghive.lib.rules
from borghive.lib.extrausers import _atomic_write, sync_extrausers
from borghive.models import Repository, SSHPublicKey
from borghive.templatetags.helpers import humanmegabytes


class LibTest(TestCase):
    """test lib functions"""

    fixtures = [
        "testing/users.yaml",
        "testing/sshpubkeys.yaml",
        "testing/repositoryusers.yaml",
        "testing/repositories.yaml",
    ]

    def test_humanmegabytes(self):
        ret = humanmegabytes("o")
        self.assertEqual(ret, "o")

        ret = humanmegabytes(50)
        self.assertEqual(ret, "50.0 MB")

        ret = humanmegabytes(1000)
        self.assertEqual(ret, "1000.0 MB")

        ret = humanmegabytes(2000)
        self.assertEqual(ret, "1.95 GB")

        ret = humanmegabytes(111111)
        self.assertEqual(ret, "108.51 GB")

        ret = humanmegabytes(1111111)
        self.assertEqual(ret, "1.06 TB")

    def test_rules(self):

        # is_owner
        repo = Repository.objects.get(name="test")
        owner = repo.owner
        owner2 = User.objects.get(username="spock")
        self.assertTrue(borghive.lib.rules.is_owner(owner, repo))
        self.assertFalse(borghive.lib.rules.is_owner(owner2, repo))

        # owned_by_group
        key = SSHPublicKey.objects.get(name="ed25519-key")
        user = User.objects.get(username="spock")
        self.assertTrue(borghive.lib.rules.owned_by_group(user, key))
        self.assertFalse(borghive.lib.rules.owned_by_group(user, repo))


class AtomicWriteTest(TestCase):
    """test _atomic_write"""

    def test_creates_file_with_content(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "passwd")
            _atomic_write(path, "hello\n")
            with open(path) as f:
                self.assertEqual(f.read(), "hello\n")

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "dir", "passwd")
            _atomic_write(path, "x\n")
            self.assertTrue(os.path.exists(path))

    def test_sets_permissions_644(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "passwd")
            _atomic_write(path, "x\n")
            mode = oct(os.stat(path).st_mode & 0o777)
            self.assertEqual(mode, oct(0o644))

    def test_cleans_up_tmp_on_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "passwd")
            with patch("os.rename", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    _atomic_write(path, "x\n")
            # only the target (which was never created) should be absent;
            # no .tmp file left behind
            leftover = [f for f in os.listdir(d) if f != os.path.basename(path)]
            self.assertEqual(leftover, [])

    def test_unlink_failure_during_cleanup_is_swallowed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "passwd")
            with patch("os.rename", side_effect=OSError("disk full")):
                with patch("os.unlink", side_effect=OSError("already gone")):
                    # The original OSError from rename must still propagate
                    with self.assertRaises(OSError):
                        _atomic_write(path, "x\n")


class SyncExtrausersTest(TestCase):
    """test sync_extrausers"""

    def _make_user(self, name, uid, group, home_suffix=None):
        u = MagicMock()
        u.name = name
        u.uid = uid
        u.group = group
        return u

    @override_settings(
        TEST_MODE=False, BORGHIVE={"EXTRAUSERS_PATH": None, "REPO_PATH": "/repos"}
    )
    def test_writes_passwd_entries(self):
        with tempfile.TemporaryDirectory() as d:
            with self.settings(BORGHIVE={"EXTRAUSERS_PATH": d, "REPO_PATH": "/repos"}):
                users = [
                    self._make_user("alice", 2000, 2000),
                    self._make_user("bob", 2001, 2001),
                ]
                sync_extrausers(users)
                with open(os.path.join(d, "passwd")) as f:
                    content = f.read()
        self.assertIn(
            "alice:x:2000:2000:Borghive Repo User:/repos/alice:/bin/bash", content
        )
        self.assertIn(
            "bob:x:2001:2001:Borghive Repo User:/repos/bob:/bin/bash", content
        )

    @override_settings(
        TEST_MODE=False, BORGHIVE={"EXTRAUSERS_PATH": None, "REPO_PATH": "/repos"}
    )
    def test_empty_user_list_writes_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            with self.settings(BORGHIVE={"EXTRAUSERS_PATH": d, "REPO_PATH": "/repos"}):
                sync_extrausers([])
                with open(os.path.join(d, "passwd")) as f:
                    content = f.read()
        self.assertEqual(content, "")

    @override_settings(TEST_MODE=True)
    def test_test_mode_skips_write(self):
        # Should return without touching the filesystem
        with patch("borghive.lib.extrausers._atomic_write") as mock_write:
            sync_extrausers([])
            mock_write.assert_not_called()
