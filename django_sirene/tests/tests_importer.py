from datetime import date, datetime, timedelta
from math import ceil

from django.test import TestCase

from ..importers import CSVEtablissementImporter, CSVUniteLegaleImporter
from ..models import Activity, Institution, Municipality
from .factories import InstitutionFactory, LegalStatusFactory


def _get_row_from_object(obj):
    row = {
        csv_field: getattr(obj, db_field)
        for csv_field, db_field in CSVEtablissementImporter.CSV_AUTO_FIELDS_MAPPING
    }
    row.update(
        {
            "etablissementSiege": "true" if obj.is_headquarter else "false",
            "dateCreationEtablissement": obj.creation_date.strftime("%Y-%m-%d")
            if obj.creation_date
            else "",
            "libelleVoieEtablissement": obj.address,
            "etatAdministratifEtablissement": "F" if obj.is_expired else "A",
            "numeroVoieEtablissement": "",
            "activitePrincipaleEtablissement": obj.activity.code[:2] + "." + obj.activity.code[2:],
            "typeVoieEtablissement": "",
            "indiceRepetitionEtablissement": "",
            "libelleCommuneEtablissement": obj.municipality.name,
            "codeCommuneEtablissement": obj.municipality.code,
            "dateDernierTraitementEtablissement": datetime.now().isoformat(),
        }
    )

    return row


BASE_ETABLISSEMENT_ROW = {
    "dateDernierTraitementEtablissement": datetime.now().isoformat(),
    "trancheEffectifsEtablissement": "5",
    "activitePrincipaleEtablissement": "AA.10A",
    "codeCommuneEtablissement": "4109",
    "codePostalEtablissement": "4000",
    "enseigne1Etablissement": "INSTITUTION TEST",
    "siret": "00000000000000",
    "dateCreationEtablissement": "1970-01-01",
    "etablissementSiege": "true",
    "etatAdministratifEtablissement": "A",
    "indiceRepetitionEtablissement": "",
    "libelleCommuneEtablissement": "NANTES",
    "libelleVoieEtablissement": "NORBERT DUPONT",
    "numeroVoieEtablissement": "75",
    "typeVoieEtablissement": "RUE",
}


BASE_UNITE_ROW = {
    "dateDernierTraitementUniteLegale": datetime.now().isoformat(),
    "siren": "000000000",
    "nicSiegeUniteLegale": "00000",
    "denominationUniteLegale": "SUPER INSTITUTION TEST",
    "categorieJuridiqueUniteLegale": "1",
}


# ETABLISSEMENT ###
class ImportEtablissementCreationTestCase(TestCase):
    def test_import_institutions_from_csv(self):
        """Assert we create institutions when import from csv
        """
        rows = [BASE_ETABLISSEMENT_ROW]
        CSVEtablissementImporter(rows).run()
        self.assertEqual(Institution.objects.count(), 1)

        institution = Institution.objects.first()
        self.assertEqual(institution.activity.code, "AA10A")
        self.assertEqual(institution.address, "75  RUE NORBERT DUPONT")
        self.assertEqual(institution.commercial_name, "INSTITUTION TEST")
        self.assertEqual(institution.creation_date, date(1970, 1, 1))
        self.assertEqual(institution.department, "04")
        self.assertTrue(institution.is_headquarter)
        self.assertEqual(institution.municipality.code, "4109")
        self.assertEqual(institution.municipality.name, "NANTES")
        self.assertEqual(institution.siret, "00000000000000")
        self.assertEqual(institution.workforce, "5")
        self.assertEqual(institution.zipcode, "04000")
        self.assertFalse(institution.is_expired)
        # will be assigned later
        self.assertEqual(institution.name, "")
        self.assertEqual(institution.headquarter, None)
        self.assertEqual(institution.legal_status, None)
        # legacy
        self.assertFalse(institution.is_hidden)

    def test_import_institutions_can_update_db(self):
        """Assert we can update institutions when import from csv
        """
        dbo = InstitutionFactory()

        row = _get_row_from_object(dbo)

        new_municipality_code = "00000"
        new_activity_code = "00.000"
        new_zipcode = str(int(dbo.zipcode) + 1).zfill(5)

        row.update(
            {
                "codePostalEtablissement": new_zipcode,
                "codeCommuneEtablissement": new_municipality_code,
                "activitePrincipaleEtablissement": new_activity_code,
            }
        )

        CSVEtablissementImporter([row]).run()

        self.assertEqual(Institution.objects.get().zipcode, new_zipcode)
        self.assertEqual(Institution.objects.get().municipality_id, new_municipality_code)
        self.assertEqual(Institution.objects.get().activity_id, "00000")

    def test_import_institutions_with_empty_value_as_related_dont_create_related(self):
        """Assert related can't have an empty value as code
        """
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update(
            {
                "activitePrincipaleEtablissement": "",
                "codeCommuneEtablissement": "",
                "libelleCommuneEtablissement": "",
            }
        )
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Municipality.objects.count(), 0)
        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(Institution.objects.count(), 1)


class ImportEtablissementUpdateTestCase(TestCase):
    def test_update_institutions_from_csv(self):
        """Assert we create institutions when import from csv
        """
        dbo = InstitutionFactory()
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"siret": dbo.siret})
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 1)

        institution = Institution.objects.first()
        self.assertEqual(institution.activity.code, "AA10A")
        self.assertEqual(institution.address, "75  RUE NORBERT DUPONT")
        self.assertEqual(institution.commercial_name, "INSTITUTION TEST")
        self.assertEqual(institution.creation_date, date(1970, 1, 1))
        self.assertNotEqual(institution.updated, dbo.updated)
        self.assertEqual(institution.department, "04")
        self.assertTrue(institution.is_headquarter)
        self.assertEqual(institution.municipality.code, "4109")
        self.assertEqual(institution.municipality.name, "NANTES")
        self.assertEqual(institution.siret, dbo.siret)
        self.assertEqual(institution.workforce, "5")
        self.assertEqual(institution.zipcode, "04000")
        self.assertFalse(institution.is_expired)
        # will be assigned later
        self.assertEqual(institution.name, dbo.name)
        self.assertEqual(institution.headquarter, dbo.headquarter)
        self.assertEqual(institution.legal_status, dbo.legal_status)
        # legacy
        self.assertFalse(institution.is_hidden)

    def test_remove_update_expire_institution(self):
        dbo = InstitutionFactory()
        row = _get_row_from_object(dbo)
        row.update({"etatAdministratifEtablissement": "F"})
        self.assertFalse(dbo.is_expired)
        old_date = dbo.updated

        CSVEtablissementImporter([row]).run()
        dbo.refresh_from_db()
        self.assertTrue(dbo.is_expired)
        self.assertNotEqual(old_date, dbo.updated)

    def test_recreate_an_expired_institution(self):
        expired = InstitutionFactory(is_expired=True)
        row = _get_row_from_object(expired)
        row.update({"etatAdministratifEtablissement": "A"})
        self.assertEqual(Institution.objects.actives().count(), 0)
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.actives().count(), 1)


class ImportEtablissementFromDateTestCase(TestCase):

    today = datetime.now()
    date_from = datetime(1990, 10, 10)
    recent = (today - timedelta(days=30)).isoformat()
    mild = (today - timedelta(days=35)).isoformat()
    old = datetime(1980, 1, 1).isoformat()

    # DEFAULT
    def test_import_row_when_date_is_after_defaut(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": self.recent})
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_dont_import_row_when_date_before_defaut(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": self.mild})
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 0)

    def test_dont_import_row_when_date_is_other_format(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": "2015/03/03"})
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 0)

    # DATE FROM
    def test_import_row_when_date_is_after_date_from(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": self.mild})
        CSVEtablissementImporter([row], date_from=self.date_from).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_dont_import_row_when_date_before_date_from(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": self.old})
        CSVEtablissementImporter([row], date_from=self.date_from).run()
        self.assertEqual(Institution.objects.count(), 0)

    # EMPTY
    def test_dont_import_row_when_date_is_empty(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": ""})
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 0)

    # FORCE
    def test_import_row_when_date_is_empty_if_force(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": ""})
        CSVEtablissementImporter([row], force=True).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_import_row_when_date_is_old_if_force(self):
        row = BASE_ETABLISSEMENT_ROW.copy()
        row.update({"dateDernierTraitementEtablissement": self.old})
        CSVEtablissementImporter([row], force=True).run()
        self.assertEqual(Institution.objects.count(), 1)


class ImportEtablissementOffsetTestCase(TestCase):

    def test_import_row_when_no_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row]).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_import_row_when_after_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row], offset=1).run()
        self.assertEqual(Institution.objects.count(), 1)

    def test_dont_import_row_when_before_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row], offset=2).run()
        self.assertEqual(Institution.objects.count(), 0)


# UNITE LEGALE ###
class ImportUniteLegaleTestCase(TestCase):
    def test_update_legal_status(self):
        ls = LegalStatusFactory()
        dbo = InstitutionFactory(legal_status=None)
        row = BASE_UNITE_ROW.copy()
        row.update(
            {
                "siren": dbo.siren,
                "nicSiegeUniteLegale": dbo.nic,
                "categorieJuridiqueUniteLegale": ls.code,
            }
        )
        CSVUniteLegaleImporter([row]).run()
        dbo.refresh_from_db()
        self.assertEqual(dbo.legal_status, ls)

    def test_update_name(self):
        dbo = InstitutionFactory(name="")
        row = BASE_UNITE_ROW.copy()
        row.update({"siren": dbo.siren, "nicSiegeUniteLegale": dbo.nic})
        CSVUniteLegaleImporter([row]).run()
        dbo.refresh_from_db()
        self.assertEqual(dbo.name, "SUPER INSTITUTION TEST")

    def test_is_headquarter(self):
        dbo = InstitutionFactory(is_headquarter=False, siret="00000000000000")
        row = BASE_UNITE_ROW.copy()
        CSVUniteLegaleImporter([row]).run()
        dbo.refresh_from_db()
        self.assertTrue(dbo.is_headquarter)
        self.assertIsNone(dbo.headquarter)

    def test_has_headquarter(self):
        hq = InstitutionFactory(siret="00000000000000")
        sub = InstitutionFactory(siret="00000000009876")
        row = BASE_UNITE_ROW.copy()
        CSVUniteLegaleImporter([row]).run()
        hq.refresh_from_db()
        sub.refresh_from_db()
        self.assertTrue(hq.is_headquarter)
        self.assertFalse(sub.is_headquarter)
        self.assertIsNone(hq.headquarter)
        self.assertEqual(sub.headquarter, hq)

    def test_update_updated(self):
        dbo = InstitutionFactory()
        old_updated_date = dbo.updated
        row = BASE_UNITE_ROW.copy()
        row.update(
            {
                "siren": dbo.siren,
                "nicSiegeUniteLegale": dbo.nic,
            }
        )
        self.assertEqual(old_updated_date, dbo.updated)
        CSVUniteLegaleImporter([row]).run()
        dbo.refresh_from_db()
        self.assertNotEqual(old_updated_date, dbo.updated)

    def test_subsidiaries_are_updated(self):
        InstitutionFactory(siret="00000000000000")
        ls = LegalStatusFactory()
        sub = InstitutionFactory(siret="00000000009876")
        row = BASE_UNITE_ROW.copy()
        row.update({"categorieJuridiqueUniteLegale": ls.code})
        CSVUniteLegaleImporter([row]).run()
        sub.refresh_from_db()
        self.assertEqual(sub.name, "SUPER INSTITUTION TEST")
        self.assertEqual(sub.legal_status, ls)


class ImportUniteLegaleFromDateTestCase(TestCase):

    today = datetime.now()
    date_from = datetime(1990, 10, 10)
    recent = (today - timedelta(days=30)).isoformat()
    mild = (today - timedelta(days=35)).isoformat()
    old = datetime(1980, 1, 1).isoformat()

    def setUp(self):
        self.dbo = InstitutionFactory(siret="00000000000000", is_headquarter=False)

    # DEFAULT
    def test_import_row_when_date_is_after_defaut(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": self.recent})
        CSVUniteLegaleImporter([row]).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)

    def test_dont_import_row_when_date_before_defaut(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": self.mild})
        CSVUniteLegaleImporter([row]).run()
        self.dbo.refresh_from_db()
        self.assertFalse(self.dbo.is_headquarter)

    # DATE FROM
    def test_import_row_when_date_is_after_date_from(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": self.mild})
        CSVUniteLegaleImporter([row], date_from=self.date_from).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)

    def test_dont_import_row_when_date_before_date_from(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": self.old})
        CSVUniteLegaleImporter([row], date_from=self.date_from).run()
        self.dbo.refresh_from_db()
        self.assertFalse(self.dbo.is_headquarter)

    # EMPTY
    def test_dont_import_row_when_date_is_empty(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": ""})
        CSVUniteLegaleImporter([row]).run()
        self.dbo.refresh_from_db()
        self.assertFalse(self.dbo.is_headquarter)

    # FORCE
    def test_import_row_when_date_is_empty_if_force(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": ""})
        CSVUniteLegaleImporter([row], force=True).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)

    def test_import_row_when_date_is_old_if_force(self):
        row = BASE_UNITE_ROW.copy()
        row.update({"dateDernierTraitementUniteLegale": self.old})
        CSVUniteLegaleImporter([row], force=True).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)


class ImportUniteLegaleOffsetTestCase(TestCase):

    def setUp(self):
        self.dbo = InstitutionFactory(siret="00000000000000", is_headquarter=False)

    def test_import_row_when_no_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row]).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)

    def test_import_row_when_after_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row], offset=1).run()
        self.dbo.refresh_from_db()
        self.assertTrue(self.dbo.is_headquarter)

    def test_dont_import_row_when_before_offset(self):
        row = BASE_ETABLISSEMENT_ROW
        CSVEtablissementImporter([row], offset=2).run()
        self.dbo.refresh_from_db()
        self.assertFalse(self.dbo.is_headquarter)


# PERFORMANCE ###
class ImportEtablissementQueriesTestCase(TestCase):

    n = 31
    nb_batch = 7
    db_batch_size = ceil(n / nb_batch)

    def test_import_etablissement(self):
        rows = [_get_row_from_object(InstitutionFactory()) for _ in range(self.n)]
        # creation
        with self.assertNumQueries(7):
            CSVEtablissementImporter(rows, filename="").run()
        self.assertEqual(Institution.objects.count(), self.n)
        self.assertEqual(Activity.objects.count(), self.n)
        self.assertEqual(Municipality.objects.count(), self.n)

        # update
        with self.assertNumQueries(5):
            CSVEtablissementImporter(rows, filename="").run()
        self.assertEqual(Institution.objects.count(), self.n)
        self.assertEqual(Activity.objects.count(), self.n)
        self.assertEqual(Municipality.objects.count(), self.n)

    def test_import_etablissement_with_batch(self):

        rows = [_get_row_from_object(InstitutionFactory()) for _ in range(self.n)]
        # creation
        with self.assertNumQueries(6 + self.nb_batch):
            CSVEtablissementImporter(rows, filename="", db_batch_size=self.db_batch_size).run()
        self.assertEqual(Institution.objects.count(), self.n)
        self.assertEqual(Activity.objects.count(), self.n)
        self.assertEqual(Municipality.objects.count(), self.n)

        # update
        with self.assertNumQueries(5):
            CSVEtablissementImporter(rows, filename="", db_batch_size=self.db_batch_size).run()
        self.assertEqual(Institution.objects.count(), self.n)
        self.assertEqual(Activity.objects.count(), self.n)
        self.assertEqual(Municipality.objects.count(), self.n)


class ImportUniteLegaleQueriesTestCase(TestCase):

    n = 31
    nb_batch = 7
    process_batch_size = ceil(n / nb_batch)

    def _get_unite_row_for_obj(self, obj):
        return {
            "dateDernierTraitementUniteLegale": datetime.now().isoformat(),
            "siren": obj.siren,
            "nicSiegeUniteLegale": obj.nic,
            "denominationUniteLegale": "SUPER INSTITUTION TEST",
            "categorieJuridiqueUniteLegale": LegalStatusFactory().code,
        }

    def test_import_unite_legale_all_are_headquarters(self):
        objs = [InstitutionFactory(is_headquarter=False) for _ in range(self.n)]
        for i, obj in enumerate(objs):
            # sirets are XX000000000000 instead of 000000000000XX
            obj.siret = (str(i) + "9").ljust(14, "0")
            obj.save()
        rows = [self._get_unite_row_for_obj(obj) for obj in objs]

        # create
        with self.assertNumQueries(3):
            CSVUniteLegaleImporter(rows, filename="").run()
        # update
        with self.assertNumQueries(3):
            CSVUniteLegaleImporter(rows, filename="").run()

        self.assertFalse(Institution.objects.filter(is_headquarter=False).exists())

    def test_import_unite_legale_all_are_headquarters_batch(self):
        objs = [InstitutionFactory(is_headquarter=False) for _ in range(self.n)]
        for i, obj in enumerate(objs):
            # sirets are XX000000000000 instead of 000000000000XX
            obj.siret = (str(i) + "9").ljust(14, "0")
            obj.save()
        rows = [self._get_unite_row_for_obj(obj) for obj in objs]

        # create
        with self.assertNumQueries(self.nb_batch * 2 + 1):
            CSVUniteLegaleImporter(
                rows,
                filename="",
                process_batch_size=self.process_batch_size,
                db_batch_size=self.process_batch_size,
            ).run()
        # update
        with self.assertNumQueries(self.nb_batch * 2 + 1):
            CSVUniteLegaleImporter(
                rows,
                filename="",
                process_batch_size=self.process_batch_size,
                db_batch_size=self.process_batch_size,
            ).run()

        self.assertFalse(Institution.objects.filter(is_headquarter=False).exists())

    def test_import_unite_legale_all_have_headquarters(self):
        rows = []
        nb_headquarters = self.n
        for i in range(nb_headquarters):
            siren = (str(i) + "9").ljust(10, "0")
            rows.append(
                self._get_unite_row_for_obj(
                    InstitutionFactory(is_headquarter=False, siret=siren + "0000")
                )
            )
            for j in range(nb_headquarters):
                InstitutionFactory(is_headquarter=False, siret=siren + str(j + 1).zfill(4))

        # create
        with self.assertNumQueries(4):
            CSVUniteLegaleImporter(rows, filename="", db_batch_size=self.n ** 2).run()
        # update
        with self.assertNumQueries(4):
            CSVUniteLegaleImporter(rows, filename="", db_batch_size=self.n ** 2).run()

        self.assertEqual(Institution.objects.filter(is_headquarter=True).count(), nb_headquarters)

    def test_import_unite_legale_all_have_headquarters_batch(self):
        rows = []
        nb_headquarters = self.n

        for i in range(nb_headquarters):
            siren = (str(i) + "9").ljust(10, "0")
            rows.append(
                self._get_unite_row_for_obj(
                    InstitutionFactory(is_headquarter=False, siret=siren + "0000")
                )
            )
            for j in range(nb_headquarters):
                InstitutionFactory(is_headquarter=False, siret=siren + str(j + 1).zfill(4))

        # create
        with self.assertNumQueries(2 * self.nb_batch + 1):
            CSVUniteLegaleImporter(
                rows,
                filename="",
                process_batch_size=self.process_batch_size,
                db_batch_size=self.n ** 2,
            ).run()
        # update
        with self.assertNumQueries(2 * self.nb_batch + 1):
            CSVUniteLegaleImporter(
                rows,
                filename="",
                process_batch_size=self.process_batch_size,
                db_batch_size=self.n ** 2,
            ).run()

        self.assertEqual(Institution.objects.filter(is_headquarter=True).count(), nb_headquarters)
