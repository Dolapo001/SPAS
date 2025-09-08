import os
import django
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from supervisors.models import Supervisor
from frontend.models import Department
from django.db import IntegrityError

User = get_user_model()


class Command(BaseCommand):
    help = 'Link existing supervisors to departments based on user authentication'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the migration without actually saving changes',
        )
        parser.add_argument(
            '--skip-duplicates',
            action='store_true',
            help='Skip supervisors that would cause duplicate key errors',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_duplicates = options['skip_duplicates']

        # Get all supervisors without a department
        supervisors_without_dept = Supervisor.objects.filter(department__isnull=True)
        self.stdout.write(
            self.style.WARNING(
                f'Found {supervisors_without_dept.count()} supervisors without department assignment'
            )
        )

        # Get all users with departments
        users_with_dept = User.objects.filter(department__isnull=False)
        user_dept_map = {user.email: user.department for user in users_with_dept}

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for supervisor in supervisors_without_dept:
            # Try to find a user with the same email as the supervisor
            if supervisor.email and supervisor.email in user_dept_map:
                department = user_dept_map[supervisor.email]

                # Check if a supervisor with same email already exists in this department
                existing_supervisor = Supervisor.objects.filter(
                    department=department,
                    email=supervisor.email
                ).first()

                if existing_supervisor:
                    if skip_duplicates:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipping supervisor "{supervisor.name}" - duplicate email "{supervisor.email}" already exists in department "{department.name}"'
                            )
                        )
                        skipped_count += 1
                        continue
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Duplicate found: Supervisor "{existing_supervisor.name}" already has email "{supervisor.email}" in department "{department.name}"'
                            )
                        )
                        error_count += 1
                        continue

                if not dry_run:
                    try:
                        supervisor.department = department
                        supervisor.save()
                        self.stdout.write(
                            f'Assigned supervisor "{supervisor.name}" to department "{department.name}"'
                        )
                        updated_count += 1
                    except IntegrityError as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Error assigning supervisor "{supervisor.name}": {str(e)}'
                            )
                        )
                        error_count += 1
                else:
                    self.stdout.write(
                        f'[DRY RUN] Would assign supervisor "{supervisor.name}" to department "{department.name}"'
                    )
                    updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'Could not find department for supervisor "{supervisor.name}" (email: {supervisor.email})'
                    )
                )
                skipped_count += 1

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nMigration complete! Updated {updated_count} supervisors, skipped {skipped_count} supervisors, {error_count} errors'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    'DRY RUN: No changes were actually saved to the database'
                )
            )