# Generated by Django 3.0.6 on 2020-06-03 10:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_sirene', '0003_auto_20180307_0802'),
    ]

    operations = [
        migrations.AlterField(
            model_name='institution',
            name='address',
            field=models.CharField(help_text='L4_NORMALISEE', max_length=127),
        ),
    ]
