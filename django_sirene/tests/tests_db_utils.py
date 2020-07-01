import mock

from django.test import TestCase

from django_sirene.db_utils import toggle_postgres_vacuum


@mock.patch("django.db.backends.utils.CursorWrapper.execute")
class ToggleVacuumTestCase(TestCase):

    def test_command_is_as_expected(self, mock_db):
        toggle_postgres_vacuum(True)
        self.assertEqual(
            mock_db.call_args.args,
            ("ALTER TABLE django_sirene_institution SET (autovacuum_enabled=True)", )
        )
        toggle_postgres_vacuum(False)
        self.assertEqual(
            mock_db.call_args.args,
            ("ALTER TABLE django_sirene_institution SET (autovacuum_enabled=False)", )
        )
