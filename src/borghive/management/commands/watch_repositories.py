import logging
import os
import sys

import inotify.adapters
from django import db
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

# used for signal activation
import borghive.signals  # pylint: disable=unused-import
from borghive.models.repository import Repository, RepositoryEvent

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-many-nested-blocks


class Command(BaseCommand):
    """
    django management command to watch borg repository changes on fs with inotify
    """

    help = "Watch Repositories for changes"

    def add_arguments(self, parser):
        """arguments parser"""
        parser.add_argument("--repo-path", type=str, default="/repos")

    def get_repo_by_path(self, path):
        """distill repo name from inotify path"""
        parts = path.split("/")
        if len(parts) < 3:  # Ensure path has at least /repos/repo_user/repo_name
            raise ValueError(f"Invalid path structure: {path}")
        repo_name = parts[-1]
        repo_user = parts[-2]
        db.close_old_connections()
        repo = Repository.objects.get(name=repo_name, repo_user__name=repo_user)
        LOGGER.debug("get_repo_by_path: %s", repo)
        return repo

    def handle(self, *args, **options):
        """
        install inotify watcher for repository directory
        this can generate a large amount of events when there are many or large repositories.
        """

        if not os.path.isdir(options["repo_path"]):
            raise CommandError(f'Repo path: {options["repo_path"]} not found')

        i = inotify.adapters.InotifyTree(options["repo_path"])

        while True and not settings.TEST_MODE:  # noqa
            try:
                for event in i.event_gen(yield_nones=False):
                    self._process_event(event, options["repo_path"])
            except PermissionError as exc:
                LOGGER.debug("Ignoring PermissionError: %s", exc)
            except borghive.models.repository.Repository.DoesNotExist as exc:
                LOGGER.debug("Ignoring not existing repo: %s", exc)
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.exception(exc)
                sys.exit(255)

    def _process_event(self, event, repo_path):
        """Process a single inotify event."""
        try:
            (_, type_names, path, filename) = event

            LOGGER.debug(
                "PATH=[%s] FILENAME=[%s] EVENT_TYPES=%s",
                path,
                filename,
                type_names,
            )

            repo = self.get_repo_by_path(path)

            if filename == "lock.roster":
                self._handle_lock_event(repo, type_names)
            elif filename == "README" and "IN_CREATE" in type_names:
                self._handle_create_event(repo)
            elif filename.startswith("index.") and "IN_MOVED_TO" in type_names:
                self._handle_update_event(repo)
            elif "IN_DELETE_SELF" in type_names and self._is_repo_path(path, repo_path):
                self._handle_delete_event(repo)

        except borghive.models.repository.Repository.DoesNotExist as exc:
            LOGGER.debug("Ignoring event for non-existing repository: %s", exc)
        except ValueError as exc:
            LOGGER.debug("Ignoring event for invalid path: %s", exc)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(exc)

    def _handle_lock_event(self, repo, type_names):
        """Handle lock file events (repo open/close)."""
        if "IN_CREATE" in type_names:
            LOGGER.info("lock created: repo open: %s", repo)
            RepositoryEvent(
                event_type="watcher", message="Repository open", repo=repo
            ).save()
        elif "IN_DELETE" in type_names:
            LOGGER.info("lock deleted: repo close: %s", repo)
            RepositoryEvent(
                event_type="watcher", message="Repository closed", repo=repo
            ).save()

    def _handle_create_event(self, repo):
        """Handle repo creation event."""
        LOGGER.info("repo created: readme created - indicates repo creation: %s", repo)
        RepositoryEvent(
            event_type="watcher", message="Repository created", repo=repo
        ).save()

    def _handle_update_event(self, repo):
        """Handle repo update event."""
        LOGGER.info("repo updated: %s", repo)
        RepositoryEvent(
            event_type="watcher", message="Repository updated", repo=repo
        ).save()

    def _handle_delete_event(self, repo):
        """Handle repo deletion event."""
        LOGGER.info("repo deleted: %s", repo)
        RepositoryEvent(
            event_type="watcher", message="Repository deleted", repo=repo
        ).save()

    def _is_repo_path(self, path, repo_path):
        """Check if the path is a repository path."""
        return len(path.replace(repo_path, "").split("/")) == 2
