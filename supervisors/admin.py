from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import Supervisor


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    list_display = ('name', 'current_students_count', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)
    readonly_fields = ('current_students_count',)

