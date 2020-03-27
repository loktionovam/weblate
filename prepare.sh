#!/usr/bin/env bash

set -euo pipefail
set -a
# shellcheck disable=SC1091
source .env
set +a


DJANGO_SETTINGS_MODULE=weblate.settings_test python3 ./manage.py migrate
DJANGO_SETTINGS_MODULE=weblate.settings_test ./manage.py createsuperuser --username admin
DJANGO_SETTINGS_MODULE=weblate.settings_test ./manage.py createsuperuser --username cibot
DJANGO_SETTINGS_MODULE=weblate.settings_test ./manage.py collectstatic --noinput
weblate/examples/celery start
