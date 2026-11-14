from django.contrib import admin

from .models import OfficeHoliday


@admin.register(OfficeHoliday)
class OfficeHolidayAdmin(admin.ModelAdmin):
    list_display = ("date", "name")
    search_fields = ("name",)
    date_hierarchy = "date"
