from django.contrib import admin
from .models import Activity, Institution, LegalStatus, Municipality


class InstitutionAdmin(admin.ModelAdmin):
    search_fields = ("siret", "name", "commercial_name")
    list_select_related = (
        "legal_status",
        "headquarter",
        "municipality",
        "activity",
    )
    list_display = (
        "siret",
        "__str__",
        "zipcode",
        "municipality",
        "headquarter",
        "is_headquarter",
        "is_expired",
        "updated",
        "created",
    )
    autocomplete_fields = ("activity", "legal_status", "municipality")
    raw_id_fields = ("headquarter",)


admin.site.register(Institution, InstitutionAdmin)


class DjangoSireneBaseAdmin:
    search_fields = ("code", "name")


class ActivityAdmin(DjangoSireneBaseAdmin, admin.ModelAdmin):
    pass


admin.site.register(Activity, ActivityAdmin)


class LegalStatusAdmin(DjangoSireneBaseAdmin, admin.ModelAdmin):
    pass


admin.site.register(LegalStatus, LegalStatusAdmin)


class MunicipalityAdmin(DjangoSireneBaseAdmin, admin.ModelAdmin):
    pass


admin.site.register(Municipality, MunicipalityAdmin)
