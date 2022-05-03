# Generated by Django 4.0.2 on 2022-04-01 15:07

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions
import pages.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pages', '0097_user_account_warning_count_user_last_warned_on'),
    ]

    operations = [
        migrations.CreateModel(
            name='Drop_File',
            fields=[
                ('file_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file_object', models.FileField(max_length=500, storage=pages.models.CustomFileSystemStorage(), upload_to=pages.models.randomize_path_drop_file)),
                ('file_name', models.CharField(blank=True, default=None, max_length=255, null=True)),
            ],
            options={
                'ordering': [django.db.models.expressions.OrderBy(django.db.models.expressions.F('file_name'), nulls_last=True)],
            },
        ),
        migrations.CreateModel(
            name='Drop_Request',
            fields=[
                ('request_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('has_encrypted', models.BooleanField(default=False)),
                ('request_info', models.CharField(blank=True, max_length=5000, null=True)),
                ('user_retrieved', models.BooleanField(default=False)),
                ('delete_on', models.DateTimeField()),
                ('request_code', models.CharField(max_length=50)),
                ('email_sent', models.BooleanField(default=False)),
                ('files', models.ManyToManyField(to='pages.Drop_File')),
                ('target_email', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='pages.email')),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
        migrations.RemoveField(
            model_name='network',
            name='classifications',
        ),
        migrations.AddField(
            model_name='network',
            name='CFTS_deployed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='request',
            name='has_encrypted',
            field=models.BooleanField(default=False),
        ),
        migrations.DeleteModel(
            name='Classification',
        ),
    ]