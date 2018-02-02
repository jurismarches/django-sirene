from django.db import models
from django.utils import timezone

from .helpers import get_nic, get_siren
from .managers import InstitutionQuerySet


class Activity(models.Model):
    """
    """
    code = models.CharField(max_length=5, primary_key=True, help_text='APET700')
    name = models.CharField(max_length=65, help_text='LIBAPET')

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class Municipality(models.Model):
    """
    """
    code = models.CharField(max_length=3, primary_key=True, help_text='COMET')
    name = models.CharField(max_length=32, help_text='LIBCOM')

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class LegalStatus(models.Model):
    """
    """
    code = models.CharField(max_length=4, primary_key=True, help_text='NJ')
    name = models.CharField(max_length=100, help_text='LIBNJ')

    def __str__(self):
        return '{} ({})'.format(self.name, self.code)


class Institution(models.Model):
    """
    """
    activity = models.ForeignKey(
        Activity,
        related_name='institutions',
        on_delete=models.PROTECT,
        null=True,
    )
    address = models.CharField(max_length=38, help_text='L4_NORMALISEE')
    commercial_name = models.CharField(max_length=50, help_text='ENSEIGNE')
    creation_date = models.DateField(help_text='DCRET', null=True)
    department = models.CharField(max_length=2, help_text='DEPET')
    headquarter = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.PROTECT,
        related_name='subsidiaries',
    )
    is_headquarter = models.BooleanField(default=False)
    legal_status = models.ForeignKey(
        LegalStatus,
        related_name='institutions',
        on_delete=models.PROTECT,
        null=True,
    )
    municipality = models.ForeignKey(
        Municipality,
        related_name='institutions',
        on_delete=models.PROTECT,
        null=True,
    )
    name = models.CharField(max_length=131, help_text='NOMEN_LONG')
    siret = models.CharField(
        max_length=14,
        db_index=True,
        unique=True,
        help_text='SIREN + NIC'
    )
    tel = models.CharField(max_length=10, null=True)
    workforce = models.CharField(max_length=6, help_text='EFETCENT')
    zipcode = models.CharField(max_length=5, help_text='CODPOS')

    created = models.DateTimeField(default=timezone.now, help_text='Created locally')
    is_expired = models.BooleanField(default=False, help_text='Removed from database')
    is_hidden = models.BooleanField(default=False, help_text='Ask to be hidden')
    updated = models.DateTimeField(auto_now=True, help_text='Updated locally')
    last_viewed_filename = models.CharField(max_length=255)

    objects = InstitutionQuerySet.as_manager()

    def __str__(self):
        return self.commercial_name if self.commercial_name else self.name

    @property
    def siren(self):
        return get_siren(self.siret)

    @property
    def nic(self):
        return get_nic(self.siret)
