# -*- coding: utf-8 -*-
"""This module automatically re-create translations
if templates changed and translates strings using
machine translation memory
"""

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import transaction
from django.http.request import HttpRequest
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from time import sleep

from weblate.addons.base import UpdateBaseAddon
from weblate.addons.events import (
    EVENT_COMPONENT_UPDATE,
    EVENT_PRE_UPDATE,
    EVENT_POST_UPDATE
)
from weblate.addons.forms import AutoAddonForm
from weblate.memory.storage import (
    CATEGORY_PRIVATE_OFFSET,
    CATEGORY_SHARED,
    CATEGORY_USER_OFFSET,
    TranslationMemory,
)
from weblate.auth.models import User
from weblate.trans.tasks import auto_translate
from weblate.logger import LOGGER
from weblate.utils.celery import extract_batch_kwargs
from weblate.utils.state import STATE_TRANSLATED

from whoosh.index import LockError


class SynchronizeTranslations(UpdateBaseAddon):
    """This class contains events handlers thats
    re-create translations and apply automatic translation
    from machine translation memory
    """

    events = (EVENT_COMPONENT_UPDATE, EVENT_PRE_UPDATE, EVENT_POST_UPDATE)
    name = "weblate_omp.addons.synchronize_translations"
    verbose = _("Synchronize translations with translation templates")
    description = _(
        "This addon based on 'Automatic Translation' addon"
        "and automatically re-create translations"
        "if templates changed and translates strings using"
        "machine translation"
    )
    settings_form = AutoAddonForm
    multiple = True
    icon = "language.svg"
    components_template_updated = []
    project_scope = True
    logger = LOGGER
    username = settings.WEBLATE_CI_USERNAME
    user = None
    request = None
    components_addon_enabled = []
    TEMPLATES = ['en', 'templates']

    @classmethod
    def can_install(cls, component, user):
        """This method used to validate the addon installation.
        Must return 'True' if plugin can be installed.
        """
        can_be_installed = True
        try:
            cls.set_user()
        except User.DoesNotExist as error:
            can_be_installed = False
        else:
            cls.set_request()
        return can_be_installed

    def component_update(self, component):
        """Handler to processing EVENT_COMPONENT_UPDATE event.
        """
        # run one-time full synchronization when addon enabled.
        if component.name not in SynchronizeTranslations.components_addon_enabled:
            SynchronizeTranslations.components_addon_enabled.append(component.name)
            self.mandatory_run_addon(component)

    def mandatory_run_addon(self, component):
        """This method mandatory import memory,
        re-create translations and apply imported
        memory to re-created translations.
        """
        self.logger.info(
            "Update translation memory for '%s' project",
            component.project
        )
        transaction.on_commit(lambda : self.import_memory(component.project_id))

        self.logger.info(
            "Start first time mandatory translations synchronization for '%s'",
            component
        )
        self.recreate_translations(component)

        self.logger.info(
            "Start first time mandatory autotranslate for '%s'",
            component
        )
        self.apply_auto_translate(component)

        self.logger.info(
            "First time mandatory translations synchronization for '%s' completed", component)

    @classmethod
    def set_request(cls):
        """Method set request object.
        """
        if not cls.request:
            cls.request = HttpRequest()
            cls.request.user = cls.user
            cls.request.session = 'session'
            messages = FallbackStorage(cls.request)
            cls.request._messages = messages

    @classmethod
    def set_user(cls):
        """Method set user object.
        """
        if not cls.user:
            cls.user = User.objects.get(username=cls.username)

    def import_memory(self, project_id):
        """This method copied from weblate.memory.tasks
        to run synchronously without task manager.
        """
        from weblate.trans.models import Unit

        units = Unit.objects.filter(
            translation__component__project_id=project_id,
            state__gte=STATE_TRANSLATED,
        )
        for unit in units.iterator():
            self.update_memory(unit)

    def update_memory(self, unit, user=None):
        """This method copied from weblate.memory.tasks
        to run synchronously without task manager.
        """
        component = unit.translation.component
        project = component.project

        categories = [CATEGORY_PRIVATE_OFFSET + project.pk]
        if user:
            categories.append(CATEGORY_USER_OFFSET + user.id)
        if unit.translation.component.project.contribute_shared_tm:
            categories.append(CATEGORY_SHARED)

        for category in categories:
            self.update_memory_task(
                source_language=project.source_language.code,
                target_language=unit.translation.language.code,
                source=unit.source,
                target=unit.target,
                origin=component.full_slug,
                category=category,
            )

    def update_memory_task(self, *args, **kwargs):
        """This method copied from weblate.memory.tasks
        to run synchronously without task manager.
        """
        def fixup_strings(data):
            result = {}
            for key, value in data.items():
                if isinstance(value, int):
                    result[key] = value
                else:
                    result[key] = force_text(value)
            return result

        data = extract_batch_kwargs(*args, **kwargs)

        memory = TranslationMemory()
        try:
            with memory.writer() as writer:
                for item in data:
                    writer.add_document(**fixup_strings(item))
        except LockError:
            # Manually handle retries, it doesn't work
            # with celery-batches
            sleep(10)
            for unit in data:
                self.update_memory_task(**unit)

    def pre_update(self, component):
        """This method is handler to processing EVENT_PRE_UPDATE event,
        i.e. before vcs update.
        Try to detect changed template files in a new
        commit (pull, rebase in the weblate interface).
        """
        # 'new_base' here is a filename of file used for creating new translations
        # i.e. template for new translations
        changed = component.repository.list_upstream_changed_files()
        if component.new_base is not None and component.new_base in changed:
            self.logger.info(
                "Source file '%s' changed, so need to re-recreate existing translations",
                component.new_base
            )
            self.components_template_updated.append(component.name)
        else:
            self.logger.info(
                "Source files don't changed, so skipping to re-create existing translation")

    def recreate_translations(self, component):
        """This method re-create all translations (i.e. delete/create) in the given component.
        """
        self.logger.info("Start re-create existing translations")
        translations_recreated = False
        for translation in component.translation_set.iterator():
            self.logger.info("Processing '%s'", translation)
            if translation.language_code in self.TEMPLATES:
                self.logger.info(
                    "Translation '%s' is template translation, so skipping",
                    translation
                )
                continue
            language = translation.language
            self.logger.info("Deletion user is: '%s'", SynchronizeTranslations.user)
            self.logger.info("Remove '%s'", translation)
            translation.remove(SynchronizeTranslations.user)
            self.logger.info("Create new translation for '%s' language", language)
            component.add_new_language(
                language=language,
                request=SynchronizeTranslations.request,
                send_signal=False)

            if not translations_recreated:
                translations_recreated = True

        return translations_recreated

    def post_update(self, component, previous_head):
        """This method is handler to processing EVENT_POST_UPDATE event,
        i.e. after vcs update.
        Try to to re-create existing translation if needed and
        'apply' translation memory to re-created translations.
        """
        if component.name in self.components_template_updated:
            # populate a translation memory before autotranslate
            self.logger.info(
                "Update translation memory for '%s' project",
                component.project
            )
            transaction.on_commit(lambda : self.import_memory(component.project_id))
            need_to_auto_translate = self.recreate_translations(component)
            if need_to_auto_translate:
                self.logger.info(
                    "Translations re-created, so start automatic translation")
                self.apply_auto_translate(component)
            else:
                self.logger.info(
                    "Translations don't re-created, so automatic translation skipped")

    def apply_auto_translate(self, component):
        """This method 'apply' machine translation
        to the given component.
        """
        self.logger.info(
            "Auto translation for '%s' component started", component.name
        )
        for translation in component.translation_set.iterator():
            if translation.is_source:
                continue
            self.logger.info(
                "Apply auto translation to '%s'", translation
            )
            transaction.on_commit(
                lambda: auto_translate.apply(
                    [SynchronizeTranslations.user.pk, translation.pk],
                    {**self.instance.configuration}
                )
            )
        self.logger.info(
            "Auto translation for '%s' component completed", component.name
        )
