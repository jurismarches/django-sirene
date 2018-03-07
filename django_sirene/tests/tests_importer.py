from django.test import TestCase

from ..helpers import get_siren
from ..importers import CSVImporter
from ..models import Institution
from .factories import InstitutionFactory


def _get_row_from_object(obj):
    row = {
        csv_field: getattr(obj, db_field)
        for csv_field, db_field in CSVImporter.CSV_AUTO_FIELDS_MAPPING
    }
    row.update({
        'SIREN': obj.siren,
        'NIC': obj.nic,
        'DCRET': obj.creation_date.strftime('%Y%m%d'),
        'LIBNJ': obj.legal_status.name,
        'LIBCOM': obj.municipality.name,
        'LIBAPET': obj.activity.name,
        'SIEGE': '1' if obj.is_headquarter else '0',
    })

    return row


class ImportStockSirenTestCase(TestCase):

    filename = '_L_M'

    @classmethod
    def setUpTestData(cls):
        cls.base_row = {
            'APET700': '9499Z',
            'CODPOS': '44000',
            'DEPCOMEN': '44109',
            'DCRET': '20171001',
            'DEPET': '44',
            'EFETCENT': '100',
            'ENSEIGNE': 'INSTITUTION TEST',
            'L4_NORMALISEE': '75 RUE NORBERT DUPONT',
            'LIBAPET': 'Administration',
            'LIBCOM': 'NANTES',
            'LIBNJ': 'SARL',
            'NIC': '00000',
            'NOMEN_LONG': 'INSTITUTION TEST',
            'NJ': '5710',
            'SIEGE': '1',
            'SIREN': '000000000',
        }

    def test_import_institutions_from_csv(self):
        """Assert we create institutions when import from csv
        """
        rows = [self.base_row]
        with self.assertNumQueries(9):  # 4 select + 4 insert + 1 select
            CSVImporter(rows, filename=self.filename, import_subsidiaries=False).run()
        self.assertEqual(Institution.objects.count(), 1)

        institution = Institution.objects.first()
        for csv_field, db_field in CSVImporter.CSV_AUTO_FIELDS_MAPPING:
            self.assertEqual(
                getattr(institution, db_field),
                self.base_row[csv_field]
            )

    def test_import_already_imported(self):
        """
        """
        rows = [self.base_row]
        with self.assertNumQueries(14):
            CSVImporter(rows, filename=self.filename).run()
        self.assertEqual(Institution.objects.count(), 1)
        with self.assertNumQueries(11):
            CSVImporter(rows, filename=self.filename).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_import_subsidiary(self):
        """Verify we link headquarter to subsidiary
        """
        institution = InstitutionFactory(is_headquarter=True)
        row = _get_row_from_object(institution)
        row.update({
            'SIEGE': '0',
            'NIC': str(int(row['NIC']) + 1),
        })
        CSVImporter([row], filename=self.filename).run()
        self.assertEqual(Institution.objects.count(), 2)
        institution.refresh_from_db()
        self.assertTrue(institution.subsidiaries.count())

    def test_cant_import_headquarter_and_subsidiaries_in_same_time(self):
        """
        """
        headquarter_row = self.base_row
        count = 10

        subsidiaries_row = []
        for i in range(1, count):
            subsidiary_row = headquarter_row.copy()
            subsidiary_row.update({
                'SIEGE': '0',
                'NIC': str(int(headquarter_row['NIC']) + i).zfill(5),
            })
            subsidiaries_row.append(subsidiary_row)

        rows = [headquarter_row] + subsidiaries_row
        CSVImporter(rows, filename=self.filename).run()
        self.assertEqual(Institution.objects.count(), count)
        for ins in Institution.objects.filter(is_headquarter=False):
            self.assertEqual(
                Institution.objects.get(is_headquarter=True).siret,
                ins.headquarter.siret,
            )

    def test_can_import_subsidiary_without_headquarter(self):
        """
        """
        subsidiary_row = self.base_row.copy()
        subsidiary_row.update({
            'SIEGE': '0',
        })
        CSVImporter([subsidiary_row], filename=self.filename).run()
        self.assertEqual(
            Institution.objects.filter(is_headquarter=False).count(), 1
        )

    def test_import_institutions_can_update_db(self):
        """Assert we can update institutions when import from csv
        """
        dbo = InstitutionFactory()

        row = _get_row_from_object(dbo)

        new_municipality_code = '00000'
        new_legal_status_code = '0000'
        new_activity_code = '00000'
        new_zipcode = str(int(dbo.zipcode) + 1).zfill(5)

        row.update({
            'CODPOS': new_zipcode,
            'DEPCOMEN': new_municipality_code,
            'APET700': new_activity_code,
            'NJ': new_legal_status_code,
        })

        CSVImporter([row], filename=self.filename).run()

        self.assertEqual(
            Institution.objects.get().zipcode,
            new_zipcode
        )
        self.assertEqual(
            Institution.objects.get().municipality_id,
            new_municipality_code
        )
        self.assertEqual(
            Institution.objects.get().activity_id,
            new_activity_code
        )
        self.assertEqual(
            Institution.objects.get().legal_status_id,
            new_legal_status_code
        )

    def test_import_institutions_with_empty_value_as_related_dont_create_related(self):
        """Assert related can't have an empty value as code
        """
        row = self.base_row.copy()
        row.update({
            'NJ': '',
            'LIBNJ': '',
            'APET700': '',
            'LIBAPET': '',
            'DEPCOMEN': '',
            'LIBCOM': '',
        })
        CSVImporter([row], filename=self.filename).run()
        self.assertEqual(
            Institution.objects.filter(legal_status__isnull=True).count(), 1
        )


class ImportUpdateFileTestCase(TestCase):

    filename = '_E_Q'

    @classmethod
    def setUpTestData(cls):
        cls.base_row = {
            'APET700': '9499Z',
            'CODPOS': '44000',
            'DEPCOMEN': '44109',
            'DCRET': '20171001',
            'DEPET': '44',
            'EFETCENT': '100',
            'ENSEIGNE': 'INSTITUTION TEST',
            'L4_NORMALISEE': '75 RUE NORBERT DUPONT',
            'LIBAPET': 'Administration',
            'LIBCOM': 'NANTES',
            'LIBNJ': 'SARL',
            'NIC': '00000',
            'NOMEN_LONG': 'INSTITUTION TEST',
            'NJ': '5710',
            'SIEGE': '1',
            'SIREN': '000000000',
        }

    def test_remove_update_expire_institution(self):
        """
        """
        dbo = InstitutionFactory()
        row = _get_row_from_object(dbo)
        row.update({
            'VMAJ': 'E',
        })
        self.assertFalse(dbo.is_expired)
        self.assertFalse(dbo.updated_from_filename)
        old_date = dbo.updated

        CSVImporter([row], filename=self.filename).run()
        dbo.refresh_from_db()
        self.assertTrue(dbo.is_expired)
        self.assertEqual(dbo.updated_from_filename, self.filename)
        self.assertNotEqual(old_date, dbo.updated)

    def test_recreate_an_expired_institution(self):
        """
        """
        expired = InstitutionFactory(is_expired=True)
        row = _get_row_from_object(expired)
        row.update({
            'VMAJ': 'C',
        })
        self.assertEqual(Institution.objects.actives().count(), 0)
        CSVImporter([row], filename=self.filename).run()
        self.assertEqual(Institution.objects.actives().count(), 1)

    def test_update_institution(self):
        """
        """
        chars = '___'
        dbo = InstitutionFactory()
        row = _get_row_from_object(dbo)
        row.update({
            'VMAJ': 'F',
            'NOMEN_LONG': dbo.name + chars
        })
        self.assertNotIn(chars, dbo.name)
        CSVImporter([row], filename=self.filename).run()
        dbo.refresh_from_db()
        self.assertIn(chars, dbo.name)

    def test_update_with_initial_row_does_not_update_institution(self):
        """
        """
        chars = '___'
        dbo = InstitutionFactory()
        row = _get_row_from_object(dbo)
        row.update({
            'VMAJ': 'I',
            'NOMEN_LONG': dbo.name + chars
        })
        self.assertNotIn(chars, dbo.name)
        CSVImporter([row], filename=self.filename).run()
        dbo.refresh_from_db()
        self.assertNotIn(chars, dbo.name)

    def test_update_when_institution_ask_to_be_hidden(self):
        """
        """
        dbo = InstitutionFactory()
        row = _get_row_from_object(dbo)
        row.update({
            'VMAJ': 'O',
        })
        self.assertFalse(dbo.is_hidden)
        CSVImporter([row], filename=self.filename).run()
        dbo.refresh_from_db()
        self.assertTrue(dbo.is_hidden)

    def test_update_when_institution_ask_to_be_visible(self):
        """
        """
        dbo = InstitutionFactory(is_hidden=True)
        row = _get_row_from_object(dbo)
        row.update({
            'VMAJ': 'D',
        })
        self.assertTrue(dbo.is_hidden)
        CSVImporter([row], filename=self.filename).run()
        dbo.refresh_from_db()
        self.assertFalse(dbo.is_hidden)

    def test_update_subsidiaries_when_import_new_headquarter(self):
        """
        """
        headquarter = InstitutionFactory()
        subsidiaries = []
        for i in range(10):
            subsidiaries.append(
                InstitutionFactory(headquarter_id=headquarter.id)
            )

        rows = []

        # expire headquarter
        row = _get_row_from_object(headquarter)
        row.update({
            'VMAJ': 'E',
        })
        rows.append(row)

        # new headquarter
        row = self.base_row.copy()
        row.update({
            'VMAJ': 'C',
            'SIREN': get_siren(headquarter.siret),
            'NIC': '99999',
        })
        rows.append(row)

        CSVImporter(rows, filename=self.filename).run()

        qs_headquarters = Institution.objects.actives().headquarters()
        self.assertEqual(qs_headquarters.count(), 1)
        new_headquarter_id = qs_headquarters.first().id
        self.assertNotEqual(
            headquarter.id,
            new_headquarter_id,
        )

        subsidiaries[0].refresh_from_db()
        self.assertEqual(subsidiaries[0].headquarter_id, new_headquarter_id)

    def test_update_subsidiaries_when_headquarter_change(self):
        """
        """
        headquarter = InstitutionFactory()
        subsidiaries = []
        for i in range(10):
            subsidiaries.append(
                InstitutionFactory(headquarter_id=headquarter.id)
            )

        rows = []

        # expire headquarter
        row = _get_row_from_object(headquarter)
        row.update({
            'VMAJ': 'E',
        })
        rows.append(row)

        # new headquarter
        row = self.base_row.copy()
        row.update({
            'VMAJ': 'F',
            'SIREN': get_siren(headquarter.siret),
            'NIC': '99999',
        })
        rows.append(row)

        CSVImporter(rows, filename=self.filename).run()

        qs_headquarters = Institution.objects.actives().headquarters()
        self.assertEqual(qs_headquarters.count(), 1)
        new_headquarter_id = qs_headquarters.first().id
        self.assertNotEqual(
            headquarter.id,
            new_headquarter_id,
        )
        subsidiaries[0].refresh_from_db()
        self.assertEqual(subsidiaries[0].headquarter_id, new_headquarter_id)
