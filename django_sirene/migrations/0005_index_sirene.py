from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_sirene', '0004_auto_20200603_1056'),
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX i_sirene ON django_sirene_institution (SUBSTRING(siret, 1, 9))",
            "DROP INDEX i_sirene"
        )
    ]