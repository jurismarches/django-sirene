from datetime import datetime
from io import StringIO

import mock
from django.core.management import call_command
from django.test import TestCase

from .mocks import FakeZfile


@mock.patch(
    "django_sirene.management.commands.populate_sirene_database.Command._get_file",
    return_value=FakeZfile(),
)
@mock.patch("django_sirene.management.commands.populate_sirene_database.CSVUniteLegaleImporter")
@mock.patch("django_sirene.management.commands.populate_sirene_database.CSVEtablissementImporter")
class PopulateSireneDatabaseTest(TestCase):

    command = "populate_sirene_database"
    out = StringIO()

    def _assert_mock_kwarg_call(self, mock, kwarg_name, value):
        self.assertEqual(mock.call_args.kwargs.get(kwarg_name), value)

    def test_command_skip_import(
        self, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        call_command(
            self.command, "--skip-StockUniteLegale", "--skip-StockEtablissement", stdout=self.out
        )
        mock_etablissement_importer.assert_not_called()
        mock_unitelegale_importer.assert_not_called()

        call_command(self.command, "--skip-StockUniteLegale", stdout=self.out)
        mock_etablissement_importer.assert_called_once()
        mock_unitelegale_importer.assert_not_called()

        call_command(self.command, "--skip-StockEtablissement", stdout=self.out)
        mock_etablissement_importer.assert_called_once()
        mock_unitelegale_importer.assert_called_once()

        call_command(self.command, stdout=self.out)
        self.assertEqual(mock_etablissement_importer.call_count, 2)
        self.assertEqual(mock_unitelegale_importer.call_count, 2)

    @mock.patch('builtins.print')
    def test_command_dry(
        self,
        mock_print,
        mock_etablissement_importer,
        mock_unitelegale_importer,
        mock_get_file
    ):
        call_command(self.command, "--dry", stdout=self.out)
        mock_etablissement_importer.assert_not_called()
        mock_unitelegale_importer.assert_not_called()
        mock_get_file.assert_not_called()
        mock_print.assert_any_call(
            "http://files.data.gouv.fr/insee-sirene/"
            "StockEtablissement_utf8.zip in etablissement.zip"
        )
        mock_print.assert_any_call(
            "http://files.data.gouv.fr/insee-sirene/"
            "StockUniteLegale_utf8.zip in unitelegale.zip"
        )

    def test_command_force(
        self, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        call_command(self.command, stdout=self.out)
        mock_etablissement_importer.assert_called_once()
        self._assert_mock_kwarg_call(mock_etablissement_importer, "force", False)
        mock_unitelegale_importer.assert_called_once()
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "force", False)
        mock_get_file.assert_called()
        self._assert_mock_kwarg_call(mock_get_file, "force", False)

        mock_etablissement_importer.reset_mock()
        mock_unitelegale_importer.reset_mock()
        mock_get_file.reset_mock()

        call_command(self.command, "--force", stdout=self.out)
        mock_etablissement_importer.assert_called_once()
        self._assert_mock_kwarg_call(mock_etablissement_importer, "force", True)
        mock_unitelegale_importer.assert_called_once()
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "force", True)
        mock_get_file.assert_called()
        self._assert_mock_kwarg_call(mock_get_file, "force", True)

    def test_command_offset(
        self, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        default = 0
        # not specified
        call_command(self.command, stdout=self.out)
        self._assert_mock_kwarg_call(mock_etablissement_importer, "offset", default)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "offset", default)
        # Bad offset
        call_command(
            self.command,
            "--offset-StockEtablissement=3.4",
            "--offset-StockUniteLegale=az",
            stdout=self.out
        )
        self._assert_mock_kwarg_call(mock_etablissement_importer, "offset", default)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "offset", default)
        # Good offsets
        call_command(
            self.command,
            "--offset-StockEtablissement=3000000",
            "--offset-StockUniteLegale=34",
            stdout=self.out
        )
        self._assert_mock_kwarg_call(mock_etablissement_importer, "offset", 3000000)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "offset", 34)

    def test_command_date_from(
        self, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        default = None
        # not specified
        call_command(self.command, stdout=self.out)
        self._assert_mock_kwarg_call(mock_etablissement_importer, "date_from", default)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "date_from", default)
        # Bad date
        call_command(self.command, "--date-from=90", stdout=self.out)
        self._assert_mock_kwarg_call(mock_etablissement_importer, "date_from", default)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "date_from", default)
        # Good date
        date = datetime(2020, 2, 1)
        call_command(self.command, "--date-from=01/02/2020", stdout=self.out)
        self._assert_mock_kwarg_call(mock_etablissement_importer, "date_from", date)
        self._assert_mock_kwarg_call(mock_unitelegale_importer, "date_from", date)

    def test_command_date_file(
        self, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        date = "2020-01-02"
        # not specified
        call_command(self.command, stdout=self.out)
        self.assertEqual(
            mock_get_file.call_args_list[0][0],
            ('etablissement.zip',
             'http://files.data.gouv.fr/insee-sirene/StockEtablissement_utf8.zip')
        )
        self.assertEqual(
            mock_get_file.call_args_list[1][0],
            ('unitelegale.zip',
             'http://files.data.gouv.fr/insee-sirene/StockUniteLegale_utf8.zip')
        )

        mock_get_file.reset_mock()

        # Date
        call_command(self.command, "--date-file=" + date, stdout=self.out)
        self.assertEqual(
            mock_get_file.call_args_list[0][0],
            ('etablissement.zip',
             'http://files.data.gouv.fr/insee-sirene/2020-01-02-StockEtablissement_utf8.zip')
        )
        self.assertEqual(
            mock_get_file.call_args_list[1][0],
            ('unitelegale.zip',
             'http://files.data.gouv.fr/insee-sirene/2020-01-02-StockUniteLegale_utf8.zip')
        )

    @mock.patch("django_sirene.management.commands.populate_sirene_database.toggle_postgres_vacuum")
    def test_db_vacuum_is_restored_even_when_import_fails(
        self, mock_vaccum, mock_etablissement_importer, mock_unitelegale_importer, mock_get_file
    ):
        mock_get_file.side_effect = Exception
        with self.assertRaises(Exception):
            call_command(self.command, stdout=self.out)
        self.assertTrue(mock_vaccum.called)
