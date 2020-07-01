from django.test import TestCase

from django_sirene.helpers import get_nic, get_siren


class HelperTestCase(TestCase):

    siret = "123456789000"

    def test_get_siren(self):
        self.assertEqual(get_siren(self.siret), "123456789")

    def test_get_nic(self):
        self.assertEqual(get_nic(self.siret), "000")
