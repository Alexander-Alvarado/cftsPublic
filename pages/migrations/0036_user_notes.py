# Generated by Django 2.1.12 on 2020-04-24 19:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0035_auto_20200420_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]
