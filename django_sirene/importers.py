import logging
import time
from collections import defaultdict
from datetime import datetime

from .helpers import get_siren
from .models import Activity, Institution, LegalStatus, Municipality

logger = logging.getLogger(__name__)


class VMAJ:
    delete = 'E'
    create = 'C'
    edit_final = 'F'
    edit_initial = 'I'
    broadcast_out = 'O'
    broadcast_in = 'D'

    update_mode = (
        delete,
        edit_final,
        broadcast_out,
        broadcast_in,
    )

    @classmethod
    def is_update_mode(cls, code):
        return code in cls.update_mode


class CSVImporter:

    CSV_AUTO_FIELDS_MAPPING = (
        ('APET700', 'activity_id'),
        ('CODPOS', 'zipcode'),
        ('COMET', 'municipality_id'),
        ('DEPET', 'department'),
        ('EFETCENT', 'workforce'),
        ('NOMEN_LONG', 'name'),
        ('ENSEIGNE', 'commercial_name'),
        ('L4_NORMALISEE', 'address'),
        ('NJ', 'legal_status_id'),
    )

    def __init__(self, rows, filename, *args, **kwargs):
        self.filename = filename
        self.rows = rows
        self.local_batch_size = kwargs.get('local_batch_size', 10000)
        self.db_batch_size = kwargs.get('db_batch_size', 100)
        self.log = kwargs.get('log', False)
        self.import_headquarters = kwargs.get('import_headquarters', True)
        self.import_subsidiaries = kwargs.get('import_subsidiaries', True)

        self.to_create = []
        self.to_update = []
        self.relateds_to_create = set()
        self.db_municipalities_code = set()
        self.db_activities_code = set()
        self.db_legal_statuses_code = set()
        self.db_headquarters = {}
        self.db_all_sirets = set()

    def _is_headquarter(self, row):
        """Is current row describe a headquarter

        :param row: dict containing the current row from csv {column: value}
        """
        return bool(int(row['SIEGE']))

    def _prepare_institution_params(self, row):
        # TODO: MAJ
        # stock = file_is_stock(filename)

        creation_date = None
        if row['DCRET']:
            creation_date = datetime.strptime(row['DCRET'], '%Y%m%d').date()

        params = {
            'siret': row['SIREN'] + row['NIC'],
            'creation_date': creation_date,
            'last_viewed_filename': self.filename,
            'is_headquarter': self._is_headquarter(row),
        }
        params.update({
            field_db: row[field_row]
            for field_row, field_db in self.CSV_AUTO_FIELDS_MAPPING
            if row[field_row]
        })

        vmaj = row.get('VMAJ', '').upper()
        if vmaj:
            if vmaj == VMAJ.delete:
                # Institution has been removed, keep it and make it expired
                params.update({
                    'is_expired': True
                })
            elif vmaj == VMAJ.create:
                # Institution has been expired previously then recreate
                params.update({
                    'is_expired': False
                })
            elif vmaj == VMAJ.broadcast_in:
                params.update({
                    'is_hidden': False
                })
            elif vmaj == VMAJ.broadcast_out:
                params.update({
                    'is_hidden': True
                })

        return params

    def _preload_data(self):
        """Load in memory some data from db
        """
        start = time.time()

        self.db_activities_code = set(Activity.objects.values_list('code', flat=True))
        self.db_legal_statuses_code = set(LegalStatus.objects.values_list('code', flat=True))
        self.db_municipalities_code = set(Municipality.objects.values_list('code', flat=True))

        qs_institutions = Institution.objects.values_list(
            'pk', 'siret', 'is_headquarter', 'is_expired'
        ).iterator()
        for pk, siret, is_headquarter, is_expired in qs_institutions:
            # take expired too to re-enable it if needed (deleted then created)
            self.db_all_sirets.add(siret)
            # but only headquarter not expired
            if is_headquarter and not is_expired:
                self.db_headquarters[get_siren(siret)] = pk

        end = time.time()
        logger.debug("Preload ran in {:0.0f}s".format(end - start))

    def _prepare_relateds(self, params, row):
        """Add relateds instance to a list to create them in bulk later

        :param params: dict containing attr of future institution instance
        :param row: dict containing the current row from csv {column: value}

        TODO: Create update method to update label of relateds
        """
        # prepare precreate municipality if needed
        municipality_id = params.get('municipality_id')
        if municipality_id and municipality_id not in self.db_municipalities_code:
            municipality = Municipality(
                code=params['municipality_id'],
                name=row['LIBCOM']
            )
            self.relateds_to_create.add(municipality)
            self.db_municipalities_code.add(municipality.code)

        # prepare precreate activities if needed
        activity_id = params.get('activity_id')
        if activity_id and activity_id not in self.db_activities_code:
            activity = Activity(
                code=activity_id,
                name=row['LIBAPET']
            )
            self.relateds_to_create.add(activity)
            self.db_activities_code.add(activity.code)

        # prepare precreate legal_status if needed
        legal_status_id = params.get('legal_status_id')
        if legal_status_id and legal_status_id not in self.db_legal_statuses_code:
            legal_status = LegalStatus(
                code=legal_status_id,
                name=row['LIBNJ']
            )
            self.relateds_to_create.add(legal_status)
            self.db_legal_statuses_code.add(legal_status.code)

    def _create_relateds(self):
        """Bulk create in DB of relateds instances

        objs: list of objects to create
        """
        # filter by class type
        filtered = defaultdict(set)
        while self.relateds_to_create:
            related_obj = self.relateds_to_create.pop()
            filtered[related_obj.__class__].add(related_obj)

        for instance, objs in filtered.items():
            instance.objects.bulk_create(objs)

    def _update_db(self):
        """Bulk create relateds in first and then Institutions
        """
        self._create_relateds()
        Institution.objects.bulk_update(
            self.to_update,
            batch_size=self.db_batch_size
        )
        self.to_update = []

    def _create_in_db(self):
        """Bulk create relateds in first and then Institutions
        """
        self._create_relateds()
        Institution.objects.bulk_create(
            self.to_create,
            batch_size=self.db_batch_size
        )
        self.to_create = []

    def _update_susidiaries_headquarter(self):
        """Update subsidiaries with expired headquarter. Link them to a new one
        """
        qs_incorrect_subsidiaries = Institution.objects.actives().filter(
            is_headquarter=False,
            headquarter__is_expired=True
        ).values_list('id', 'siret')

        incorrect_subsidiaries = defaultdict(list)
        for id_sub, siret in qs_incorrect_subsidiaries:
            incorrect_subsidiaries[get_siren(siret)].append(id_sub)

        if incorrect_subsidiaries:
            for siren_sub, ids_sub in incorrect_subsidiaries.items():
                new_headquarter_id = Institution.objects.headquarters().actives()\
                    .filter(
                        siret__startswith=siren_sub
                ).values_list('id', flat=True)

                if len(new_headquarter_id) == 0:
                    logger.warning(
                        "Can't find an actives headquarter for this siren:%s",
                        siren_sub
                    )
                    continue
                elif len(new_headquarter_id) > 1:
                    logger.warning(
                        "Find multiple actives headquarter for this siren:%s",
                        siren_sub
                    )
                    continue

                Institution.objects.actives().filter(
                    is_headquarter=False,
                    id__in=ids_sub
                ).update(
                    headquarter_id=new_headquarter_id[0]
                )

    def _run(self, headquarters_import):

        self._preload_data()

        start = time.time()
        for i, row in enumerate(self.rows, 1):
            if headquarters_import != self._is_headquarter(row):
                # we don't import headquarters and subsidiaries in same time
                continue

            vmaj = row.get('VMAJ', '').upper()
            if vmaj == VMAJ.edit_initial:
                # ignore this line because it's the initial state we want only
                # the finale state where VMAJ = 'F'
                continue

            current_siret = row['SIREN'] + row['NIC']

            already_exists = current_siret in self.db_all_sirets

            params = self._prepare_institution_params(row)

            if not self._is_headquarter(row):
                # get headquarter, sometimes headquarter is removed
                # but not subsidiaries
                pk_headquarter = self.db_headquarters.get(row['SIREN'])
                if pk_headquarter:
                    params.update({
                        'headquarter_id': pk_headquarter,
                    })

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

            # make some log
            if self.log and i % self.local_batch_size == 0:
                end = time.time()
                items_by_sec = self.local_batch_size / (end - start)
                logger.debug(
                    'Treated {} rows ({:0.0f} items/sec)'.format(i, items_by_sec),
                )
                start = time.time()

        # Create/update remaining objects
        self._create_in_db()
        self._update_db()

        # repair subsidiaries
        self._update_susidiaries_headquarter()

    def run(self):
        """
        """
        if self.import_headquarters:
            self._run(headquarters_import=True)
        if self.import_subsidiaries:
            self._run(headquarters_import=False)
