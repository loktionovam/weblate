from __future__ import absolute_import, unicode_literals

from celery import Celery

app = Celery('weblate_omp.addons', include=['weblate_omp.addons.tasks'])

app.config_from_object('django.conf:settings', namespace='CELERY')

if __name__ == '__main__':
    app.start()
