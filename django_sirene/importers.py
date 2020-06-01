import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models.functions import Substr

from .models import Activity, Institution, LegalStatus, Municipality

logger = logging.getLogger(__name__)


class BaseImporter:
    def __init__(self, rows, *args, **kwargs):
        self.rows = rows
        self.date_from = kwargs.get("date_from") or datetime.now() - timedelta(days=32)

        self.log_batch_size = kwargs.get("log_batch_size", 10000)
        self.db_batch_size = kwargs.get("db_batch_size", 100)
        self.force = kwargs.get("force", False)
        self.log = kwargs.get("log", False)

        self.offset = kwargs.get("offset", 0)

        self.relateds_to_create = set()

    def _preload_data(self):
        """
        Treatment done once before parsing the file.
        """
        return

    def _create_relateds(self):
        """Bulk create in DB of related instances
        """
        # filter by class type
        filtered = defaultdict(set)
        while self.relateds_to_create:
            related_obj = self.relateds_to_create.pop()
            filtered[related_obj.__class__].add(related_obj)

        for instance, objs in filtered.items():
            instance.objects.bulk_create(objs)

    def run(self):
        """
        Entry point :
        preload data and parse rows
        """
        start = time.time()
        self._preload_data()
        for i, row in enumerate(self.rows, 1):

            if i < self.offset:
                continue

            self._run_row(i, row)

            # make some log
            if self.log and i % self.log_batch_size == 0:
                end = time.time()
                items_by_sec = self.log_batch_size / (end - start)
                logger.info(
                    "Treated %d rows (%d items/sec)", i, items_by_sec,
                )
                start = time.time()


class CSVEtablissementImporter(BaseImporter):

    CSV_AUTO_FIELDS_MAPPING = (
        ("siret", "siret"),
        ("enseigne1Etablissement", "commercial_name"),
        ("trancheEffectifsEtablissement", "workforce"),
        ("codeCommuneEtablissement", "municipality_id"),
    )

    def __init__(self, rows, *args, **kwargs):
        super().__init__(rows, *args, **kwargs)

        self.local_batch_size = kwargs.get('local_batch_size', 10000)

        self.to_create = []
        self.to_update = []
        self.db_municipalities_code = set()
        self.db_activities_code = set()
        self.db_legal_statuses_code = set()
        self.db_all_sirets = set()

    def _is_headquarter(self, row):
        """Is current row describe a headquarter

        :param row: dict containing the current row from csv {column: value}
        """
        return row["etablissementSiege"].lower() == "true"

    def _prepare_institution_params(self, row):
        try:
            creation_date = datetime.strptime(row["dateCreationEtablissement"], "%Y-%m-%d").date()
        except ValueError:
            creation_date = None
        address = " ".join(
            [
                row["numeroVoieEtablissement"],
                row["indiceRepetitionEtablissement"],
                row["typeVoieEtablissement"],
                row["libelleVoieEtablissement"],
            ]
        )

        params = {
            "creation_date": creation_date,
            "is_headquarter": self._is_headquarter(row),
            "is_expired": row["etatAdministratifEtablissement"].upper() == "F",
            "address": address,
            "department": row.get("codeCommuneEtablissement", "")[:-3].zfill(2),
            "zipcode": row.get("codePostalEtablissement", "").zfill(5),
            "activity_id": row.get("activitePrincipaleEtablissement", "").replace(".", "") or None
        }
        params.update(
            {
                field_db: row[field_row]
                for field_row, field_db in self.CSV_AUTO_FIELDS_MAPPING
                if row[field_row]
            }
        )

        return params

    def _preload_data(self):
        """Load in memory some data from db
        """
        start = time.time()

        self.db_activities_code = set(Activity.objects.values_list("code", flat=True))
        self.db_legal_statuses_code = set(LegalStatus.objects.values_list("code", flat=True))
        self.db_municipalities_code = set(Municipality.objects.values_list("code", flat=True))
        self.db_all_sirets = set(Institution.objects.values_list("siret", flat=True))

        end = time.time()
        logger.debug("Preload finished after {:0.0f}s".format(end - start))

    def _prepare_relateds(self, params, row):
        """Add relateds instance to a list to create them in bulk later

        :param params: dict containing attr of future institution instance
        :param row: dict containing the current row from csv {column: value}

        TODO: Create update method to update label of relateds
        """
        # prepare precreate municipality if needed
        municipality_id = params.get("municipality_id")
        if municipality_id and municipality_id not in self.db_municipalities_code:
            municipality = Municipality(
                code=municipality_id, name=row["libelleCommuneEtablissement"]
            )
            self.relateds_to_create.add(municipality)
            self.db_municipalities_code.add(municipality.code)

        # prepare precreate activity if needed
        # we will get its name in an other way
        activity_id = params.get("activity_id")
        if activity_id and activity_id not in self.db_activities_code:
            activity = Activity(code=activity_id, name="")
            self.relateds_to_create.add(activity)
            self.db_activities_code.add(activity.code)

    def _create_in_db(self):
        """Bulk create relateds in first and then Institutions
        """
        self._create_relateds()
        Institution.objects.bulk_create(self.to_create, batch_size=self.db_batch_size)
        logger.info("%s institutions created", len(self.to_create))
        self.to_create = []

    def _update_db(self):
        """Bulk create relateds in first and then update Institutions
        """
        self._create_relateds()
        Institution.objects.bulk_update_no_pk(self.to_update, batch_size=self.db_batch_size)
        logger.info("%s institutions updated", len(self.to_update))
        self.to_update = []

    def _run_row(self, index, row):
        """
        Treatment for 1 row of the file
        """
        # Filter by date to lighten the import
        try:
            last_update = datetime.fromisoformat(row["dateDernierTraitementEtablissement"])
            is_fresh = last_update and last_update >= self.date_from
        except ValueError:
            is_fresh = False

        if not is_fresh and not self.force:
            return

        already_exists = row["siret"] in self.db_all_sirets
        params = self._prepare_institution_params(row)
        self._prepare_relateds(params, row)

        new_institution = Institution(**params)
        if already_exists:
            self.to_update.append(new_institution)
        else:
            self.to_create.append(new_institution)

        # treat in batch to control memory consumption
        if len(self.to_create) >= self.local_batch_size:
            self._create_in_db()
        if len(self.to_update) >= self.local_batch_size:
            self._update_db()

    def run(self):
        super().run()

        # Create/update remaining objects
        self._create_in_db()
        self._update_db()


class CSVUniteLegaleImporter(BaseImporter):
    def __init__(self, rows, *args, **kwargs):
        super().__init__(rows, *args, **kwargs)

        self.process_batch_size = kwargs.get("process_batch_size", 2000)

        self.db_legal_statuses_code = set()

        self.to_update = []
        self.batch = []

    def _preload_data(self):
        start = time.time()

        self.db_legal_statuses_code = set(LegalStatus.objects.values_list("code", flat=True))

        end = time.time()
        logger.debug("Preload finished after {:0.0f}s".format(end - start))

    def prepare_data_for_batch(self, sirens):
        """
        Retrieve relevant institutions for the batch
        """
        start = time.time()

        db_batch_data = (
            Institution.objects.annotate(db_siren=Substr("siret", 1, 9))
            .filter(db_siren__in=sirens)
            .only("siret", "pk")
        )
        self.db_batch_minimal_data = defaultdict(list)
        for obj in db_batch_data:
            self.db_batch_minimal_data[obj.db_siren].append(obj)

        end = time.time()
        logger.debug("Preload for batch finished after {:0.0f}s".format(end - start))
        return db_batch_data

    def _prepare_relateds(self, params):
        """Add relateds instance to a list to create them in bulk later

        :param params: dict containing attr of future institution instance
        :param row: dict containing the current row from csv {column: value}
        """
        # prepare precreate legal status if needed
        legal_status_id = params.get("legal_status_id")
        if legal_status_id and legal_status_id not in self.db_legal_statuses_code:
            legal_status = LegalStatus(code=legal_status_id, name="")
            self.relateds_to_create.add(legal_status)
            self.db_legal_statuses_code.add(legal_status.code)

    def update_headquarter(self, headquarter, institutions):
        for institution in institutions:
            if institution.pk == headquarter.pk:
                institution.is_headquarter = True
                institution.headquarter_id = None
            else:
                institution.is_headquarter = False
                institution.headquarter_id = headquarter.pk

    def _update_db(self):
        """Bulk create relateds in first and then Institutions
        """
        self._create_relateds()
        Institution.objects.bulk_update(
            self.to_update,
            ["name", "legal_status_id", "is_headquarter", "headquarter_id", "updated"],
            batch_size=self.db_batch_size,
        )
        logger.info("%s institutions updated", len(self.to_update))
        self.to_update = []

    def process_batch(self):
        """
        Treatment for a batch :
        retrieve relevant institutions and update them
        """
        # prepare data
        batch_sirens = [row["siren"] for row in self.batch]
        self.prepare_data_for_batch(batch_sirens)

        for row in self.batch:
            institutions = self.db_batch_minimal_data[row["siren"]]
            headquarter = None
            # update name and legal status
            # and get headquarter
            for insitution in institutions:
                insitution.name = row["name"]
                insitution.updated = datetime.now()
                insitution.legal_status_id = row["legal_status_id"] or None
                self._prepare_relateds({"legal_status_id": row["legal_status_id"]})
                if insitution.siret == row["siren"] + row["nic"]:
                    headquarter = insitution

            if headquarter:
                self.update_headquarter(headquarter, institutions)

            self.to_update.extend(institutions)

        # apply
        self._update_db()

        # reset
        self.batch = []

    def _run_row(self, index, row):
        """
        Treatment for 1 row of the file
        """
        # Filter by date to lighten the import
        try:
            last_update = datetime.fromisoformat(row["dateDernierTraitementUniteLegale"])
            is_fresh = last_update and last_update >= self.date_from
        except ValueError:
            is_fresh = False

        if not is_fresh and not self.force:
            return

        # get data
        self.batch.append(
            {
                "siren": row["siren"],
                "nic": row["nicSiegeUniteLegale"],
                "name": row["denominationUniteLegale"],
                "legal_status_id": row["categorieJuridiqueUniteLegale"],
            }
        )

        # process
        if len(self.batch) % self.process_batch_size == 0:
            self.process_batch()

    def run(self):
        super().run()

        self.process_batch()
