import datetime

from django.test import TestCase

from ..management.commands.populate_sirene_database import Command


class CommandTestCase(TestCase):

    def test_get_filenames(self):
        """Verify files to downloaded are correct
        """
        expected = [
            'sirene_201802_L_M.zip',
            'sirene_2018059_E_Q.zip',
            'sirene_2018060_E_Q.zip',
            'sirene_2018061_E_Q.zip',
            'sirene_2018064_E_Q.zip',
            'sirene_2018065_E_Q.zip',
        ]
        result = Command()._get_filenames(at=datetime.date(2018, 3, 15))
        self.assertListEqual(result, expected)
