# Generated by Django 4.0.3 on 2022-06-29 16:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0102_alter_file_user_oneeye_alter_file_user_twoeye_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='network',
            options={'ordering': ['sort_order', 'name']},
        ),
    ]