# allocation/management/commands/check_group_duplicates.py
from django.core.management.base import BaseCommand
from django.db.models import Count
from allocation.models import Group
from django.db import transaction

class Command(BaseCommand):
    help = "Detect duplicate Groups per (supervisor, department). Optionally resolve."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resolve",
            action="store_true",
            help="Attempt to resolve duplicates by deleting extras (dry-run unless --apply given)."
        )
        parser.add_argument(
            "--keep",
            choices=["first", "last"],
            default="first",
            help="When resolving, keep the 'first' (oldest) or 'last' (newest) group."
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually delete duplicate groups. Without --apply, command only prints what it WOULD do."
        )

    def handle(self, *args, **options):
        duplicates = Group.objects.values("supervisor_id", "department_id") \
            .annotate(cnt=Count("id")).filter(cnt__gt=1)

        if not duplicates:
            self.stdout.write(self.style.SUCCESS("No duplicate (supervisor, department) group pairs found."))
            return

        self.stdout.write(self.style.WARNING(f"Found {duplicates.count()} duplicate (supervisor, department) pairs:"))
        for dup in duplicates:
            sup_id = dup["supervisor_id"]
            dept_id = dup["department_id"]
            cnt = dup["cnt"]
            self.stdout.write(f"- Supervisor {sup_id} / Department {dept_id} -> {cnt} groups")

            groups = Group.objects.filter(supervisor_id=sup_id, department_id=dept_id).order_by("created_at")
            keep = groups.first() if options["keep"] == "first" else groups.last()
            remove_qs = groups.exclude(pk=keep.pk)

            self.stdout.write(f"  candidate to keep: id={keep.pk} name={keep.name} created_at={keep.created_at}")
            self.stdout.write(f"  would remove {remove_qs.count()} group(s): {[g.pk for g in remove_qs]}")

            if options["resolve"]:
                if not options["apply"]:
                    self.stdout.write(self.style.NOTICE("  (dry-run) pass --apply to actually delete these groups."))
                    continue

                # APPLY deletions: but be careful — we should reassign students before deleting.
                with transaction.atomic():
                    # If you want to preserve students, reassign them to the kept group:
                    for to_remove in remove_qs:
                        members = list(to_remove.students.all())
                        if members:
                            self.stdout.write(f"    Reassigning {len(members)} students from group {to_remove.pk} to {keep.pk}")
                            keep.students.add(*members)
                        self.stdout.write(f"    Deleting group {to_remove.pk}")
                        to_remove.delete()

                self.stdout.write(self.style.SUCCESS(f"  Resolved duplicates for sup {sup_id} dept {dept_id} (kept {keep.pk})"))
        self.stdout.write(self.style.SUCCESS("Done."))
