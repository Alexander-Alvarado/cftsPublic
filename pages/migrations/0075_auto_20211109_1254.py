# Generated by Django 3.2.8 on 2021-11-09 17:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0074_auto_20211109_0644'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='emails',
            new_name='destination_emails',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='email',
            new_name='source_email',
        ),
    ]
