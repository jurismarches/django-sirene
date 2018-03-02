from django_elasticsearch_dsl import fields

from .models import Activity, Institution, LegalStatus, Municipality

_properties_code_name = {
    'code': fields.StringField(),
    'name': fields.StringField(),
}


class InstitutionDocumentMixin:
    """TODO: Inherit from this class and DocType in your project to put institutions
    in Elasticsearch index with django-elasticsearch-dsl
    """

    name = fields.StringField(
        analyzer='french',
        fields={'raw': fields.StringField(index='not_analyzed')}
    )
    commercial_name = fields.StringField(
        analyzer='french',
        fields={'raw': fields.StringField(index='not_analyzed')}
    )

    legal_status = fields.ObjectField(properties=_properties_code_name)
    activity = fields.ObjectField(properties=_properties_code_name)
    activity = fields.ObjectField(properties=_properties_code_name)

    class Meta:
        model = Institution
        fields = [
            'address',
            'department',
            'is_expired',
            'is_headquarter',
            'is_hidden',
            'siret',
            'zipcode',
        ]
        queryset_pagination = 10000

        related_models = (
            LegalStatus,
            Municipality,
            Activity,
        )

    def get_queryset(self):
        return super().get_queryset().select_related(
            'activity',
            'municipality',
            'legal_status',
        )

    def get_instances_from_related(self, related_instance):
        return related_instance.institutions.all()
