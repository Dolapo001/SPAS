from django.db import models
from django.db.models import Q
from frontend.models import Department


class Supervisor(models.Model):
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,  # consider models.SET_NULL if you want to keep supervisors when a Department is deleted
        related_name="supervisors",
        null=True, blank=True
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "name"],
                name="unique_supervisor_name_per_department"
            ),
            # enforce uniqueness of (department, email) only when email is not NULL
            models.UniqueConstraint(
                fields=["department", "email"],
                name="unique_supervisor_email_per_department",
                condition=~Q(email=None)
            ),
        ]

    def __str__(self):
        # safe __str__ — won't error if department is None
        dept_name = self.department.name if self.department else "No department"
        return f"{self.name} ({dept_name})"

    @property
    def current_students_count(self) -> int:
        return self.students.count()
