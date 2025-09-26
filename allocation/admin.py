from django.contrib import admin
from .models import Group, AllocationResult


class GroupInline(admin.TabularInline):
    model = Group
    extra = 0
    readonly_fields = ['number', 'supervisor', 'average_grade']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class DepartmentFilter(admin.SimpleListFilter):
    title = 'Department'
    parameter_name = 'department'

    def lookups(self, request, model_admin):
        # Import here to avoid circular imports
        from frontend.models import Department
        departments = Department.objects.all()
        return [(dept.id, dept.name) for dept in departments]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(groups__department_id=self.value()).distinct()
        return queryset


@admin.register(AllocationResult)
class AllocationResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'method', 'num_groups', 'department', 'total_students_allocated']
    list_filter = [DepartmentFilter, 'method', 'created_at']
    readonly_fields = ['created_at', 'method', 'num_groups', 'department_info']
    inlines = [GroupInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with department for efficient filtering
        from django.db.models import Count, Max
        return qs.annotate(
            department_count=Count('groups__department', distinct=True)
        )

    def department(self, obj):
        # Get the first department (assuming one allocation per department)
        groups = obj.groups.all()
        if groups.exists():
            return groups.first().department
        return "No Department"

    department.short_description = 'Department'

    def total_students_allocated(self, obj):
        return sum(group.students.count() for group in obj.groups.all())

    total_students_allocated.short_description = 'Total Students'

    def department_info(self, obj):
        departments = set()
        for group in obj.groups.all():
            if group.department:
                departments.add(group.department.name)
        return ", ".join(departments) if departments else "No Departments"

    department_info.short_description = 'Departments'


class GroupAdmin(admin.ModelAdmin):
    list_display = ['number', 'supervisor', 'department', 'allocation_result', 'student_count', 'average_grade_display']
    list_filter = ['department', 'allocation_result', 'supervisor']
    readonly_fields = ['average_grade_display']
    search_fields = ['number', 'supervisor__name', 'students__name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('supervisor', 'department', 'allocation_result').prefetch_related('students')

    def student_count(self, obj):
        return obj.students.count()

    student_count.short_description = 'Students'

    def average_grade_display(self, obj):
        return f"{obj.average_grade:.2f}"

    average_grade_display.short_description = 'Average Grade'


admin.site.register(Group, GroupAdmin)