# Generated by Django 3.2.8 on 2021-12-17 15:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0088_file_pull'),
    ]

    operations = [
        migrations.AddField(
            model_name='file',
            name='scan_results',
            field=models.JSONField(blank=True, null=True),
        ),
    ]