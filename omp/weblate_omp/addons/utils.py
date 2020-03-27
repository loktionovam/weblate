from __future__ import unicode_literals

import logging

from weblate.addons.models import ADDONS, Addon
from weblate.auth.models import User
from weblate.trans.models import Project

logger = logging.getLogger('weblate_omp.addons.utils')


def check_addon_configuration(component, addon, configuration):
    """This method the part of the upstream addon installer handler.
    Check if addon configuration valid, if not then raise exception.
    """
    if addon.has_settings:
        form = addon.get_add_form(component, data=configuration)
        if not form.is_valid():
            for error in form.non_field_errors():
                logger.error(error)
            for field in form:
                for error in field.errors:
                    logger.error("Error in '%s': '%s'", field.name, error)
            raise Exception('Invalid addon configuration!')


def get_all_projects():
    """This method returns all weblate projects slug as list.
    """
    return Project.objects.all().values_list('slug', flat=True)


def install_addon(project, component, addon, user, configuration=None):
    """Install the given addon to project/component.
    """

    if addon.can_install(component, user):
        addons = Addon.objects.filter_component(component).filter(name=addon.name)
        if not addons.exists():
            logger.info(
                "Addon '%s' doesn't exists on '%s' component, create it.",
                addon.name,
                component
            )
            check_addon_configuration(component, addon, configuration)
            addon.create(component, configuration=configuration)
            addon.component_update(component)
        else:
            logger.info(
                "Addon '%s' already exists on '%s' component",
                addon.name,
                component
            )


def install_addon_for_projects(
        addon_name,
        username,
        project_slug_list=None,
        configuration=None):
    """Install the given addon to projects.
    """
    try:
        addon = ADDONS[addon_name]()
    except KeyError:
        raise Exception('Addon not found: {}'.format(addon_name))

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Exception('Can not find {} username'.format(username))

    if project_slug_list is None:
        project_slug_list = get_all_projects()

    for project_slug in project_slug_list:
        project = Project.objects.get(slug=project_slug)
        for component in project.component_set.iterator():
            install_addon(project, component, addon, user, configuration)
            if addon.project_scope:
                break
