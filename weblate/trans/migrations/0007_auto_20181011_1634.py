# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-10-11 14:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("trans", "0006_suggestion_userdetails")]

    operations = [
        migrations.AlterField(
            model_name="change",
            name="action",
            field=models.IntegerField(
                choices=[
                    (0, "Resource update"),
                    (1, "Translation completed"),
                    (2, "Translation changed"),
                    (5, "New translation"),
                    (3, "Comment added"),
                    (4, "Suggestion added"),
                    (6, "Automatic translation"),
                    (7, "Suggestion accepted"),
                    (8, "Translation reverted"),
                    (9, "Translation uploaded"),
                    (10, "Glossary added"),
                    (11, "Glossary updated"),
                    (12, "Glossary uploaded"),
                    (13, "New source string"),
                    (14, "Component locked"),
                    (15, "Component unlocked"),
                    (16, "Detected duplicate string"),
                    (17, "Committed changes"),
                    (18, "Pushed changes"),
                    (19, "Reset repository"),
                    (20, "Merged repository"),
                    (21, "Rebased repository"),
                    (22, "Failed merge on repository"),
                    (23, "Failed rebase on repository"),
                    (28, "Failed push on repository"),
                    (24, "Parse error"),
                    (25, "Removed translation"),
                    (26, "Suggestion removed"),
                    (27, "Search and replace"),
                    (29, "Suggestion removed during cleanup"),
                    (30, "Source string changed"),
                    (31, "New string added"),
                    (32, "Mass state change"),
                    (33, "Changed visibility"),
                    (34, "Added user"),
                    (35, "Removed user"),
                    (36, "Translation approved"),
                    (37, "Marked for edit"),
                ],
                default=2,
            ),
        )
    ]
