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
        """
        Safe getter that:
        1. Prefers an annotated value attached to the instance (__dict__).
        2. Uses a private attribute if the setter stored one.
        3. Falls back to common reverse manager names (students, student_set).
        4. Dynamically inspects _meta to find a one-to-many relation to Student.
        Always returns an int.
        """
        # 1) Django attaches annotation into __dict__ when using annotate()
        annotated = self.__dict__.get('current_students_count', None)
        if isinstance(annotated, int):
            return annotated

        # 2) Use private attr set by setter or view
        private = getattr(self, "_annotated_current_students_count", None)
        if isinstance(private, int):
            return private

        # 3) Common reverse manager names
        try:
            if hasattr(self, "students"):
                return self.students.count()
        except Exception:
            pass
        try:
            if hasattr(self, "student_set"):
                return self.student_set.count()
        except Exception:
            pass

        # 4) Dynamic detection via _meta (find one_to_many relation to Student)
        for rel in self._meta.get_fields():
            if getattr(rel, "one_to_many", False) and getattr(rel, "related_model", None):
                if rel.related_model.__name__ == "Student":
                    try:
                        mgr = getattr(self, rel.get_accessor_name())
                        return mgr.count()
                    except Exception:
                        continue

        # 5) Fallback
        return 0

    @current_students_count.setter
    def current_students_count(self, value):
        """
        Accept assignment from Django annotate (or manual assignments).
        Store as a private int so the getter can return it.
        """
        try:
            self._annotated_current_students_count = int(value) if value is not None else 0
        except (TypeError, ValueError):
            self._annotated_current_students_count = 0

