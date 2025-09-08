# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import School, Department, User


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'code')
    list_filter = ('school',)
    search_fields = ('name', 'code', 'school__name')
    ordering = ('school', 'name')


class CustomUserAdmin(UserAdmin):
    # Customize the form and fields displayed
    model = User
    list_display = ('email', 'first_name', 'last_name', 'department', 'is_department_admin', 'is_staff')
    list_filter = ('is_department_admin', 'is_staff', 'is_superuser', 'is_active', 'department')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_department_admin', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
        ('Department Info', {'fields': ('department',)}),
        ('Security', {'fields': ('secret_question', 'secret_answer')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'department', 'is_department_admin')}
        ),
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_readonly_fields(self, request, obj=None):
        # Make secret_answer readonly to prevent viewing the hashed value
        if obj:
            return ('secret_answer',)
        return ()

    def secret_answer(self, obj):
        # Display that the answer is hashed without showing the actual value
        if obj.secret_answer:
            return format_html('<span style="color:gray">Hashed value (not visible)</span>')
        return "Not set"
    secret_answer.short_description = 'Secret Answer'

# Unregister the default User admin if needed, then register our custom one


admin.site.register(User, CustomUserAdmin)



