import datetime
import string

import factory
from factory import fuzzy

from .. import models


class ActivityFactory(factory.DjangoModelFactory):
    code = fuzzy.FuzzyText(length=5)
    name = fuzzy.FuzzyText(length=10)

    class Meta:
        model = models.Activity


class MunicipalityFactory(factory.DjangoModelFactory):
    code = fuzzy.FuzzyText(length=5)
    name = fuzzy.FuzzyText(length=10)

    class Meta:
        model = models.Municipality


class LegalStatusFactory(factory.DjangoModelFactory):
    code = fuzzy.FuzzyText(length=4)
    name = fuzzy.FuzzyText(length=20)

    class Meta:
        model = models.LegalStatus


class InstitutionFactory(factory.DjangoModelFactory):
    siret = factory.Sequence(lambda n: '{}'.format(n).zfill(14))

    name = factory.Sequence(lambda n: 'name-{}'.format(n))
    commercial_name = factory.Sequence(lambda n: 'commercial_name-{}'.format(n))
    address = factory.Sequence(lambda n: '{} route vers Mars'.format(n))
    zipcode = '44000'
    department = '44'
    workforce = fuzzy.FuzzyInteger(low=1, high=999999)
    creation_date = fuzzy.FuzzyDate(start_date=datetime.date(2000, 1, 1))

    municipality = factory.SubFactory(MunicipalityFactory)
    activity = factory.SubFactory(ActivityFactory)
    legal_status = factory.SubFactory(LegalStatusFactory)

    class Meta:
        model = models.Institution
