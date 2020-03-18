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

from __future__ import unicode_literals

from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from weblate.addons.events import EVENT_COMPONENT_UPDATE, EVENT_DAILY, EVENT_PRE_UPDATE, EVENT_POST_UPDATE
from weblate.addons.forms import AutoAddonForm
from weblate.trans.tasks import auto_translate
from weblate.addons.base import UpdateBaseAddon
from weblate.auth.models import User
from weblate.logger import LOGGER


class AutoTranslateAddon(UpdateBaseAddon):
    events = (EVENT_COMPONENT_UPDATE, EVENT_DAILY, EVENT_PRE_UPDATE, EVENT_POST_UPDATE)
    name = "weblate.autotranslate.autotranslate"
    verbose = _("Synchronize translations with translation templates")
    description = _(
        "This addon based on 'Automatic Translation' addon"
        "and automatically re-create translation"
        "if templates changed and translates strings using"
        "machine translation"
    )
    settings_form = AutoAddonForm
    multiple = True
    icon = "language.svg"
    remove_user = None
    is_need_to_auto_translate = False
    is_templates_updated = False
    project_scope = True
    logger = LOGGER

    @classmethod
    def can_install(cls, component, user):
        cls.remove_user = user
        return True

    def component_update(self, component):
        self.daily(component)

    def pre_update(self, component):
        source_translation = component.get_source_translation()
        changed = component.repository.list_upstream_changed_files()
        self.logger.info("Check if a source file '%s' exists in changed '%s' files", source_translation.filename, changed)
        if source_translation.filename in changed:
            self.logger.info("Source file '%s' changed, so need to re-recreate existing translations", source_translation.filename)
            self.is_templates_updated = True
        else:
            self.logger.info("Source files don't changed, so skipping to re-create existing translation")

    def post_update(self, component, previous_head):
        if self.is_templates_updated:
            self.logger.info("Start re-create existing translations")
            is_need_to_auto_translate = False
            for translation in component.translation_set.iterator():
                self.logger.info("Processing '%s'", translation)
                if translation.is_source:
                    self.logger.info("Translation '%s' is source translation, so skipping", translation)
                    continue
                else:
                    language = translation.language
                    # when used cli python ./manage.py updategit --all
                    # 'remove_user' is None and command fails
                    # AttributeError: 'NoneType' object has no attribute 'get_author_name'
                    # so use 'admin' user here if remove_user is None
                    if self.__class__.remove_user is None:
                        remove_user = User.objects.get(username='admin')
                    else:
                        remove_user = self.__class__.remove_user
                    self.logger.info("Deletion user is: '%s'", remove_user)

                    self.logger.info("Remove '%s'", translation)
                    translation.remove(remove_user)
                    self.logger.info("Create new translation for '%s' language", language)
                    component.add_new_language(language, None, send_signal=False)
                    if not is_need_to_auto_translate:
                        is_need_to_auto_translate = True

            if is_need_to_auto_translate:
                self.logger.info("Translations re-created, so start automatic translation")
                self.daily(component)
            else:
                self.logger.info("Translations don't re-created, so automatic translation skipped")

    def daily(self, component):
        for translation in component.translation_set.iterator():
            if translation.is_source:
                continue
            transaction.on_commit(
                lambda: auto_translate.delay(
                    None, translation.pk, **self.instance.configuration
                )
            )
