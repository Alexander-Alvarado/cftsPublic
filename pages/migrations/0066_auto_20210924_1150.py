# Generated by Django 2.1.12 on 2021-09-24 15:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0065_merge_20210924_1147'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='rejection',
            options={'ordering': ['sort_order']},
        ),
        migrations.AddField(
            model_name='rejection',
            name='sort_order',
            field=models.IntegerField(default=99),
        ),
    ]