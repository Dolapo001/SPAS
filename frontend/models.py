# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
import secrets
from django.contrib.auth.hashers import make_password, check_password

from frontend.managers import CustomUserManager


class School(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    class Meta:
        unique_together = ("school", "name")  # Ensures department names are unique within a school

    def __str__(self):
        return f"{self.school.name} - {self.name}"


class User(AbstractUser):
    # Remove username field and use email instead
    username = None
    email = models.EmailField(unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)

    # Make secret fields optional so management commands don't fail.
    secret_question = models.CharField(max_length=255, blank=True, null=True)
    secret_answer = models.CharField(max_length=255, blank=True, null=True)  # Will be hashed

    is_department_admin = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # no prompts other than email & password

    objects = CustomUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['department'],
                condition=models.Q(is_department_admin=True),
                name='unique_department_admin'
            )
        ]

    def save(self, *args, **kwargs):
        if self.secret_answer and not self.secret_answer.startswith("pbkdf2_sha256$"):
            self.secret_answer = make_password(self.secret_answer)
        super().save(*args, **kwargs)

    def check_secret_answer(self, raw_answer):
        if not self.secret_answer:
            return False
        return check_password(raw_answer, self.secret_answer)

    @staticmethod
    def get_random_secret_question():
        questions = [
            "What was the name of your first pet?",
            "What city were you born in?",
            "What is your mother's maiden name?",
            "What was your favorite subject in high school?",
            "What is the name of your favorite childhood friend?",
        ]
        return secrets.choice(questions)
