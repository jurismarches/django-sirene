from django_bulk_update.query import BulkUpdateQuerySet
import logging

logger = logging.getLogger(__name__)


class InstitutionQuerySet(BulkUpdateQuerySet):

    # field name to exclude
    excluded_fields = frozenset([
        'id',
        'updated',
        'created',
        'siret',
    ])

    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self.update_fields = set()
        for f in self.model._meta.fields:
            if f.name not in self.excluded_fields:
                self.update_fields.add(f.name)
                self.update_fields.add(f.column)

    def headquarters(self):
        return self.filter(is_headquarter=True)

    def actives(self):
        return self.filter(is_expired=False)

    def bulk_update(self, objs, batch_size=None):
        """Find modified instances and build a queryset with them

        :param data: list Institutions
        """
        if not objs:
            return

        institutions_by_siret = {
            o.siret: o
            for o in objs
        }
        institutions = self.filter(
            siret__in=set(institutions_by_siret.keys())
        )

        # First loop to verify if update is required
        siret_require_update = set()
        for institution in institutions:
            obj = institutions_by_siret[institution.siret]
            for fieldname, value in obj.__dict__.items():
                if fieldname not in self.update_fields:
                    continue

                if str(getattr(institution, fieldname)) != str(value):
                    logger.debug(
                        'Add %s because %s change - old:%s, new:%s' % (
                            institution.siret,
                            fieldname,
                            getattr(institution, fieldname),
                            value,
                        )
                    )
                    siret_require_update.add(institution.siret)
                    break

        # Second loop to update only required
        if siret_require_update:
            institutions_to_update = self.filter(
                siret__in=siret_require_update
            )
            for institution in institutions_to_update:
                obj = institutions_by_siret[institution.siret]
                for fieldname, value in obj.__dict__.items():
                    if fieldname in self.update_fields:
                        setattr(institution, fieldname, value)

            super().bulk_update(
                institutions_to_update,
                batch_size=batch_size,
                update_fields=self.update_fields,
            )
