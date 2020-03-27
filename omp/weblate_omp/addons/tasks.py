from __future__ import absolute_import, unicode_literals

from .celery import app
from .utils import get_all_projects, install_addon_for_projects


@app.task
def install_addon_for_projects_task(
        addon_name,
        username,
        project_slug_list=None,
        configuration=None):

    install_addon_for_projects(
        addon_name,
        username,
        project_slug_list,
        configuration
    )
