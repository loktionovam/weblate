# -*- coding: utf-8 -*-
#
# Copyright © 2012 - 2020 Michal Čihař <michal@cihar.com>
#
# This file is part of Weblate <https://weblate.org/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

#
# Django settings for running testsuite
#

import os
import warnings

from weblate.settings_example import *  # noqa

CI_DATABASE = os.environ.get('CI_DATABASE', '')

default_user = 'weblate'
default_name = 'weblate'
if CI_DATABASE == 'mysql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
    default_user = 'root'
    DATABASES['default']['OPTIONS'] = {
        'init_command': (
            'SET NAMES utf8, '
            'wait_timeout=28800, '
            'default_storage_engine=INNODB, '
            'sql_mode="STRICT_TRANS_TABLES"'
        ),
        'charset': 'utf8',
        'isolation_level': 'read committed',
    }
elif CI_DATABASE == 'postgresql':
    DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
    default_user = 'postgres'
else:
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
    default_name = 'weblate.db'
    # Workaround for
    # https://github.com/travis-ci/travis-ci/issues/7873
    if 'TRAVIS' in os.environ:
        DATABASES['default']['TEST'] = {'NAME': 'weblate_test.db'}

DATABASES['default']['HOST'] = os.environ.get('CI_DB_HOST', '')
DATABASES['default']['NAME'] = os.environ.get('CI_DB_NAME', default_name)
DATABASES['default']['USER'] = os.environ.get('CI_DB_USER', default_user)
DATABASES['default']['PASSWORD'] = os.environ.get('CI_DB_PASSWORD', '')
DATABASES['default']['PORT'] = os.environ.get('CI_DB_PORT', '')

# Configure admins
ADMINS = (('Weblate test', 'noreply@weblate.org'),)

# Different root for test repos
DATA_DIR = os.path.join(BASE_DIR, 'data-test')
MEDIA_ROOT = os.path.join(DATA_DIR, 'media')
STATIC_ROOT = os.path.join(DATA_DIR, 'static')
CELERY_BEAT_SCHEDULE_FILENAME = os.path.join(DATA_DIR, 'celery', 'beat-schedule')
CELERY_TASK_ALWAYS_EAGER = False
# CELERY_BROKER_URL = 'memory://'
# CELERY_TASK_EAGER_PROPAGATES = True
REDIS_PROTO = 'redis'
REDIS_PASSWORD = ""

CELERY_BROKER_URL = "{}://{}{}:{}/{}".format(
    REDIS_PROTO,
    ":{}@".format(REDIS_PASSWORD) if REDIS_PASSWORD else "",
    os.environ.get("REDIS_HOST", "127.0.0.1"),
    os.environ.get("REDIS_PORT", "6379"),
    os.environ.get("REDIS_DB", "2"),
)
if REDIS_PROTO == "rediss":
    CELERY_BROKER_URL = "{}?ssl_cert_reqs={}".format(
        CELERY_BROKER_URL,
        "CERT_REQUIRED" if get_env_bool("REDIS_VERIFY_SSL", True) else "CERT_NONE",
    )
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

CELERY_TASK_ROUTES = {
    "weblate.trans.search.*": {"queue": "search"},
    "weblate.trans.tasks.optimize_fulltext": {"queue": "search"},
    "weblate.trans.tasks.cleanup_fulltext": {"queue": "search"},
    "weblate.trans.tasks.auto_translate": {"queue": "translate"},
    "weblate.memory.tasks.*": {"queue": "memory"},
    "weblate.accounts.tasks.notify_*": {"queue": "notify"},
    "weblate.accounts.tasks.send_mails": {"queue": "notify"},
    "weblate.memory.tasks.memory_backup": {"queue": "backup"},
    "weblate.utils.tasks.settings_backup": {"queue": "backup"},
    "weblate.utils.tasks.database_backup": {"queue": "backup"},
    "weblate.wladmin.tasks.backup": {"queue": "backup"},
    "weblate.wladmin.tasks.backup_service": {"queue": "backup"},
}

# Silent logging setup
DEFAULT_LOG = "console"
DEBUG = True
HAVE_SYSLOG = False

if DEBUG or not HAVE_SYSLOG:
    DEFAULT_LOG = "console"
else:
    DEFAULT_LOG = "syslog"

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/stable/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "formatters": {
        "syslog": {"format": "weblate[%(process)d]: %(levelname)s %(message)s"},
        "simple": {"format": "%(levelname)s %(message)s"},
        "logfile": {"format": "%(asctime)s %(levelname)s %(message)s"},
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "syslog": {
            "level": "DEBUG",
            "class": "logging.handlers.SysLogHandler",
            "formatter": "syslog",
            "address": "/dev/log",
            "facility": SysLogHandler.LOG_LOCAL2,
        },
        # Logging to a file
        # 'logfile': {
        #     'level':'DEBUG',
        #     'class':'logging.handlers.RotatingFileHandler',
        #     'filename': "/var/log/weblate/weblate.log",
        #     'maxBytes': 100000,
        #     'backupCount': 3,
        #     'formatter': 'logfile',
        # },
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins", DEFAULT_LOG],
            "level": "ERROR",
            "propagate": True,
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
        # Logging database queries
        # 'django.db.backends': {
        #     'handlers': [DEFAULT_LOG],
        #     'level': 'DEBUG',
        # },
        "weblate": {
            "handlers": [DEFAULT_LOG],
            "level": os.environ.get("WEBLATE_LOGLEVEL", "DEBUG"),
        },
        # Logging search operations
        "weblate.search": {"handlers": [DEFAULT_LOG], "level": "INFO"},
        # Logging VCS operations
        "weblate.vcs": {"handlers": [DEFAULT_LOG], "level": "WARNING"},
        # Python Social Auth
        "social": {"handlers": [DEFAULT_LOG], "level": "DEBUG" if DEBUG else "WARNING"},
        # Django Authentication Using LDAP
        "django_auth_ldap": {
            "level": "DEBUG" if DEBUG else "WARNING",
            "handlers": [DEFAULT_LOG],
        },
    },
}

if not HAVE_SYSLOG:
    del LOGGING["handlers"]["syslog"]

# Reset caches
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}

# Selenium can not clear HttpOnly cookies in MSIE
SESSION_COOKIE_HTTPONLY = False

# Use database backed sessions for transaction consistency in tests
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Use weak password hasher in tests, there is no point in spending CPU time
# in hashing test passwords
PASSWORD_HASHERS = ['django.contrib.auth.hashers.CryptPasswordHasher']

# Test optional apps as well
INSTALLED_APPS += ('weblate.billing', 'weblate.legal')

# Test GitHub auth
AUTHENTICATION_BACKENDS = (
    'social_core.backends.email.EmailAuth',
    'social_core.backends.github.GithubOAuth2',
    'weblate.accounts.auth.WeblateUserBackend',
)

AUTH_VALIDATE_PERMS = True

warnings.filterwarnings(
    'error',
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r'django\.db\.models\.fields',
)

# Generate junit compatible XML for AppVeyor
if 'APPVEYOR' in os.environ:
    TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
    TEST_OUTPUT_FILE_NAME = 'junit.xml'

WEBLATE_ADDONS = [
    "weblate.addons.gettext.GenerateMoAddon",
    "weblate.addons.gettext.UpdateLinguasAddon",
    "weblate.addons.gettext.UpdateConfigureAddon",
    "weblate.addons.gettext.MsgmergeAddon",
    "weblate.addons.gettext.GettextCustomizeAddon",
    "weblate.addons.gettext.GettextAuthorComments",
    "weblate.addons.cleanup.CleanupAddon",
    "weblate.addons.consistency.LangaugeConsistencyAddon",
    "weblate.addons.discovery.DiscoveryAddon",
    "weblate.addons.flags.SourceEditAddon",
    "weblate.addons.flags.TargetEditAddon",
    "weblate.addons.flags.SameEditAddon",
    "weblate.addons.flags.BulkEditAddon",
    "weblate.addons.generate.GenerateFileAddon",
    "weblate.addons.json.JSONCustomizeAddon",
    "weblate.addons.properties.PropertiesSortAddon",
    "weblate.addons.git.GitSquashAddon",
    "weblate.addons.removal.RemoveComments",
    "weblate.addons.removal.RemoveSuggestions",
    "weblate.addons.resx.ResxUpdateAddon",
    "weblate.addons.yaml.YAMLCustomizeAddon",
    "weblate.addons.autotranslate.AutoTranslateAddon",
]

WEBLATE_ADDONS += (
#   'weblate_omp.addons.synchronize.SynchronizeTranslations',
    'weblate.addons.synchronize.SynchronizeTranslations',
)

WEBLATE_CI_USERNAME = os.environ.get('WEBLATE_CI_USERNAME')
# TIME_ZONE = "Europe/Moscow"
