from django.contrib import admin
from .models import Institution


class InstitutionAdmin(admin.ModelAdmin):
    search_fields = (
        'siret',
    )
    list_select_related = (
        'legal_status',
        'headquarter',
        'municipality',
        'activity',
    )
    list_display = (
        'siret',
        '__str__',
        'zipcode',
        'municipality',
        'headquarter',
        'is_headquarter',
        'is_expired',
        'updated',
        'created',
        'last_viewed_filename',
    )


admin.site.register(Institution, InstitutionAdmin)
