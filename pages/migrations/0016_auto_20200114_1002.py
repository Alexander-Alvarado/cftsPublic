# Generated by Django 2.1.12 on 2020-01-14 15:02

from django.db import migrations, models
import pages.models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0015_auto_20200114_0958'),
    ]

    operations = [
        migrations.AlterField(
            model_name='file',
            name='file_object',
            field=models.FileField(upload_to=pages.models.randomize_path),
        ),
    ]