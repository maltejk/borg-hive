import datetime
import os
import tempfile

import unittest
from unittest import mock, skip

from django.conf import settings
from django.test import Client
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

import borghive.exceptions
import borghive.tasks
from borghive.models import Repository, RepositoryEvent, RepositoryStatistic
from borghive.forms import RepositoryForm


class RepositoryCreateTest(TestCase):

    fixtures = ["testing/users.yaml", "testing/sshpubkeys.yaml"]

    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.get_or_create(username="admin")[0])

    def test_get(self):
        response = self.client.get(reverse("repository-create"))
        self.assertEqual(response.status_code, 200)

    def test_create_repo(self):
        data = {"name": "testrepo", "ssh_keys": "2", "location": "1", "mode": "BORG"}
        response = self.client.post(reverse("repository-create"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Repository.objects.count(), 1)

    def test_injection(self):
        data = {"name": 'asdf"asd\'l\'""fk', "ssh_keys": "2", "location": "1"}
        response = self.client.post(reverse("repository-create"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Repository.objects.count(), 0)

    def test_create_crazy_repo(self):
        data = {"name": "$6ç342lA/%=075akse!!½%#@", "ssh_keys": "2", "location": "1"}
        response = self.client.post(reverse("repository-create"), data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Repository.objects.count(), 0)


class RepositoryTest(TestCase):

    fixtures = [
        "testing/users.yaml",
        "testing/sshpubkeys.yaml",
        "testing/repositoryusers.yaml",
        "testing/repositories.yaml",
    ]

    def test_refresh_exception(self):
        repo = Repository.objects.first()
        with self.assertRaises(borghive.exceptions.RepositoryNotCreated):
            repo.refresh()

    def test_repo_delete(self):
        repo = Repository.objects.first()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.BORGHIVE["REPO_PATH"] = temp_dir
            path = repo.get_repo_path()
            os.makedirs(path)
            self.assertTrue(os.path.isdir(path))
            with self.captureOnCommitCallbacks(execute=True):
                repo.delete()
            self.assertFalse(os.path.isdir(path))

    def test_repo_delete_broker_failure_does_not_raise(self):
        """a broker outage during post_delete cleanup must not stop the
        Repository row itself from being deleted"""
        repo = Repository.objects.first()
        repo_id = repo.id
        with mock.patch.object(
            borghive.tasks.repository_delete,
            "delay",
            side_effect=ConnectionError("broker down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                repo.delete()
        self.assertFalse(Repository.objects.filter(id=repo_id).exists())

    def test_repo_delete_view_broker_failure_returns_no_500(self):
        """RepositoryDeleteView must not surface a 500 when the celery
        broker is unreachable during the post_delete signal"""
        self.client = Client()
        self.client.force_login(User.objects.get_or_create(username="admin")[0])
        repo = Repository.objects.first()
        with mock.patch.object(
            borghive.tasks.repository_delete,
            "delay",
            side_effect=ConnectionError("broker down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("repository-delete", args=[repo.id])
                )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Repository.objects.filter(id=repo.id).exists())

    def test_repo_size(self):
        repo = Repository.objects.first()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.BORGHIVE["REPO_PATH"] = temp_dir
            path = repo.get_repo_path()
            os.makedirs(path + "/data")
            with open(path + "/data/test", "wb") as out:
                out.seek((1024 * 1024 * 1024) - 1)
                out.write(b"\0")
            self.assertTrue(os.path.isdir(path))
            size = borghive.tasks.get_repo_size(repo.id)
            self.assertEqual(size, 1.0)

    def test_repo_statistic_create(self):
        repo = Repository.objects.first()
        with tempfile.TemporaryDirectory() as temp_dir:
            settings.BORGHIVE["REPO_PATH"] = temp_dir
            path = repo.get_repo_path()
            os.makedirs(path + "/data")
            open(path + "/config", "a").close()
            open(path + "/index.1", "a").close()
            self.assertTrue(os.path.isdir(path))
            borghive.tasks.create_repo_statistic(repo.id)
            self.assertEqual(repo.repositorystatistic_set.count(), 1)

    @skip("TODO")
    def test_valid_refresh(self):
        repo = Repository.objects.first()
        repo_size_before = None
        repo.refresh()


class RepositoryEventTest(TestCase):

    fixtures = [
        "testing/users.yaml",
        "testing/sshpubkeys.yaml",
        "testing/repositoryusers.yaml",
        "testing/repositories.yaml",
    ]

    @skip("TODO")
    def test_event_repo_statistic_create(self):
        import borghive.signals

        repo = Repository.objects.first()
        log_event = RepositoryEvent(
            event_type="watcher", message="Repository updated", repo=repo
        )
        log_event.save()
        print(RepositoryStatistic.objects.all())

        self.assertEqual(RepositoryStatistic.objects.filter(repo=repo).count(), 1)
