# Generated by Django 2.1.12 on 2020-03-31 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0028_auto_20200225_1703'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='network',
            options={'ordering': ['sort_order']},
        ),
        migrations.AddField(
            model_name='network',
            name='sort_order',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
