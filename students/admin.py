from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('matric_no', 'cgpa', 'classification', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('matric_no',)
    ordering = ('-cgpa',)
    readonly_fields = ('classification',)

    def classification(self, obj):
        return obj.classification()
    classification.short_description = 'Classification'
