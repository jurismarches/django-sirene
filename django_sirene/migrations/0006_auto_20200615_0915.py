# Generated by Django 3.0.7 on 2020-06-15 09:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_sirene', '0005_index_sirene'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='institution',
            name='tel',
        ),
        migrations.RemoveField(
            model_name='institution',
            name='updated_from_filename',
        ),
    ]
