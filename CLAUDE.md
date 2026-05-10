# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Borg Hive is a Django-based web management interface for [borgbackup](https://www.borgbackup.org/) repositories. It manages SSH keys, borg repos, and backup notifications, and exposes both a traditional Django UI and a REST API.

## Commands

### Testing

Tests require SQLite mode and eager Celery tasks. The test runner targets the `src/` directory:

```bash
# Run all tests with coverage
TEST_MODE=True DEBUG=True CELERY_TASK_ALWAYS_EAGER=True coverage run src/manage.py test src

# Run a single test module
TEST_MODE=True DEBUG=True CELERY_TASK_ALWAYS_EAGER=True python src/manage.py test src.borghive.tests.test_repo

# Run a single test class
TEST_MODE=True DEBUG=True CELERY_TASK_ALWAYS_EAGER=True python src/manage.py test src.borghive.tests.test_repo.RepositoryTest

# Run a single test method
TEST_MODE=True DEBUG=True CELERY_TASK_ALWAYS_EAGER=True python src/manage.py test src.borghive.tests.test_repo.RepositoryTest.test_refresh_exception
```

### Linting and Formatting

```bash
black src               # format code
black src --check       # check formatting without modifying
pylama src              # lint (pylint + pycodestyle)
```

Max line length is 200 (configured in `setup.cfg`). Pylama skips `manage.py`, `core/`, `tests/`, and `migrations/`.

### Database Migrations

```bash
python src/manage.py makemigrations
python src/manage.py migrate
```

### Development Environment

The full dev stack runs in Docker Compose (MySQL, Redis, LDAP, SSH container):

```bash
docker-compose -f docker-compose.dev.yml up -d db   # start DB first (needs init time)
docker-compose -f docker-compose.dev.yml up -d
docker exec -it borg-hive_app_1 /bin/bash
./manage.py createsuperuser
```

App runs at http://localhost:8000.

## Architecture

### Project Layout

`src/` contains the Django project with three components:
- `core/` — Django project config only (`settings.py`, `urls.py`, `celery.py`). Not an installable app.
- `borghive/` — Main Django app: UI views, models, forms, tasks, management commands.
- `api/` — Django REST Framework app: serializers, viewsets, router.

### Runtime Processes

Four processes run in production (see `docker-compose.yml`):
1. **app** — Django/uWSGI web server
2. **worker** — Celery worker + beat scheduler (handles async tasks and periodic jobs)
3. **watcher** — `./manage.py watch_repositories` — inotify loop watching `/repos/` for filesystem changes
4. **borg** — SSH container with sshd; authenticates via LDAP and serves borg repositories

### Object Permission System

All models use `django-rules` for object-level permissions. The permission model is consistent throughout:

- `BaseModel` mixes in `RulesModelMixin` — every model that inherits it can define `rules_permissions` in its `Meta` class.
- `Repository.Meta.rules_permissions` shows the pattern: `add` requires `is_authenticated`; `view/change/delete` require `is_owner | owned_by_group`.
- `BaseView` combines `AutoPermissionRequiredMixin` (enforces rules) with `OwnerFilterMixin` (restricts querysets to owner or group).
- `OwnerOrGroupManager` on `Repository` provides `.by_owner_or_group(user)` for explicit queryset filtering.

When adding new models that need access control, follow the same pattern: inherit `BaseModel`, add `rules_permissions` to `Meta`, use `BaseView` in views.

### Repository → RepositoryUser → LDAP chain

Each `Repository` has a `OneToOne` link to a `RepositoryUser`. When a `RepositoryUser` is saved, it auto-generates a unique 8-character username and a UID in the range 1111–99999, then syncs to LDAP (`RepositoryLdapUser`) so sshd can authenticate the user. This sync is skipped when `TEST_MODE=True`.

The `authorized_keys_check` management command is called by sshd's `AuthorizedKeysCommand` to generate the `authorized_keys` entries for each repo user from the database. The format differs by repository mode:
- `BORG` mode: wraps each key with `borg serve --restrict-to-repository <path>`
- `IMPORT/EXPORT` mode: wraps with `rrsync -wo` or `rrsync -ro`

### Signal-Driven Side Effects

`borghive/signals.py` wires up the reactive behavior:
- `post_save(User)` → creates `AlertPreference` (alert interval/expiration settings per user)
- `post_save/delete(RepositoryUser)` → LDAP sync/delete
- `post_delete(Repository)` → fires `repository_delete` Celery task to remove files from `/repos/`
- `post_save(RepositoryEvent)` where `event_type=watcher` and message contains "Repository updated" → fires `create_repo_statistic` Celery task

The watcher process (`watch_repositories`) creates `RepositoryEvent` records in response to inotify events on the `/repos/` tree. The signal handler then reacts to those events to trigger statistics refresh.

### Notification Polymorphism

`Notification` uses `django-polymorphic` as the base class. Concrete types are `EmailNotification` and `PushoverNotification`. Each subclass stores a `form_class` attribute (string name) and a `n_type` attribute. `NotificationCreateView` looks up the model and form by the `n_type` URL parameter; `NotificationUpdateView` retrieves the real type via `Notification.objects.get(id=pk)._meta.model`.

### API App

The `api` app uses DRF with a router. All viewsets inherit from `SimpleHyperlinkedModelViewSet` which auto-generates serializers. Each viewset overrides `get_queryset` to enforce the owner/group filter. The `RepositoryViewSet` adds two extra actions: `/repositories/{id}/events/` and `/repositories/{id}/statistics/`.

API URLs are mounted at `/api/` and UI URLs at `/` (via `borghive.urls`).

### Forms

`BaseForm` automatically filters `ModelChoiceField` and `ModelMultipleChoiceField` querysets to objects accessible by the current user (owner or group). All forms that reference related objects should inherit from `BaseForm` and receive `owner` and `user` kwargs.

### Test Fixtures

Tests use YAML fixtures in `src/borghive/fixtures/testing/`: `users.yaml`, `sshpubkeys.yaml`, `repositoryusers.yaml`, `repositories.yaml`. These are loaded per `TestCase` class via the `fixtures` attribute.

### Settings and Environment

Key environment variables (defaults in `settings.py`):
- `TEST_MODE=True` — switches DB to SQLite, disables LDAP sync
- `CELERY_TASK_ALWAYS_EAGER=True` — runs Celery tasks synchronously (required for tests)
- `DEBUG=True/False` — also switches email backend to dummy
- `BORGHIVE_REPO_PATH` — filesystem path for repository storage (default `/repos`)
- `CONFIG_PATH` — SSH host key config dir (default `/config`)
- Database: `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`
- LDAP: `LDAP_HOST`, `LDAP_USER`, `LDAP_PASSWORD`, `BORGHIVE_LDAP_USER_BASEDN`
