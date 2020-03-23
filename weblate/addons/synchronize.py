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
from django.utils.translation import ugettext_lazy as _
from weblate.addons.base import UpdateBaseAddon
from weblate.addons.events import EVENT_COMPONENT_UPDATE, EVENT_DAILY, EVENT_PRE_UPDATE, EVENT_POST_UPDATE
from weblate.addons.forms import AutoAddonForm
from weblate.memory.tasks import import_memory
from weblate.auth.models import User
from weblate.trans.tasks import auto_translate
from weblate.logger import LOGGER


class SynchronizeTranslations(UpdateBaseAddon):
    """This class contains events handlers thats
    re-create translations and apply automatic translation
    from machine translation memory
    """

    events = (EVENT_COMPONENT_UPDATE, EVENT_DAILY, EVENT_PRE_UPDATE, EVENT_POST_UPDATE)
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
    templates_updated = False
    project_scope = True
    logger = LOGGER
    username = settings.WEBLATE_CI_USERNAME
    user = None
    request = None
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
        self.update_translation_memory(component)
        self.logger.info(
            "Start first time mandatory translations synchronization for '%s'", component)
        self.recreate_translations(component)
        self.logger.info("Start first time mandatory autotranslate for '%s'", component)
        self.daily(component)

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

    def update_translation_memory(self, component):
        self.logger.info("Update translation memory for '%s' project", component.project)
        transaction.on_commit(lambda: import_memory.delay(component.project_id))

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
                "Source file '%s' changed, so need to re-recreate existing translations", component.new_base)
            self.templates_updated = True
        else:
            self.logger.info(
                "Source files don't changed, so skipping to re-create existing translation")

    def recreate_translations(self, component):
        self.logger.info("Start re-create existing translations")
        translations_recreated = False
        for translation in component.translation_set.iterator():
            self.logger.info("Processing '%s'", translation)
            if translation.language_code in self.TEMPLATES:
                self.logger.info(
                    "Translation '%s' is template translation, so skipping", translation)
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
        if self.templates_updated:
            # populate a translation memory before autotranslate
            self.update_translation_memory(component)
            need_to_auto_translate = self.recreate_translations(component)
            if need_to_auto_translate:
                self.logger.info(
                    "Translations re-created, so start automatic translation")
                self.daily(component)
            else:
                self.logger.info(
                    "Translations don't re-created, so automatic translation skipped")

    def daily(self, component):
        """This method 'apply' machine translation
        to given component.
        """
        for translation in component.translation_set.iterator():
            if translation.is_source:
                continue
            transaction.on_commit(
                lambda: auto_translate.delay(
                    SynchronizeTranslations.user.pk, translation.pk, **self.instance.configuration
                )
            )
