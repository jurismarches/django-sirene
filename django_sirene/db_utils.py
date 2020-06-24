from django.db import connection


def toggle_postgres_vacuum(autovacuum_enabled):
    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE django_sirene_institution SET (autovacuum_enabled={autovacuum_enabled})"
        )
