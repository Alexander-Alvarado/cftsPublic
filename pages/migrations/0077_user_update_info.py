# Generated by Django 3.2.8 on 2021-11-19 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0076_auto_20211119_0830'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='update_info',
            field=models.BooleanField(default=True),
        ),
    ]