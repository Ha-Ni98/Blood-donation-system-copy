# Phase B - Sprint 1: Rebuild BloodRequest model
# This migration deletes the old BloodRequest table (dev only, no data preservation)
# and recreates it with the schema-compliant structure.

import django.db.models.deletion
from django.db import migrations, models


def clear_old_blood_requests(apps, schema_editor):
    """Delete all existing BloodRequest rows before schema change."""
    BloodRequest = apps.get_model('blood', 'BloodRequest')
    BloodRequest.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('blood', '0001_initial'),
    ]

    operations = [
        # Step 1: Clear existing data
        migrations.RunPython(clear_old_blood_requests, migrations.RunPython.noop),

        # Step 2: Remove old fields
        migrations.RemoveField(model_name='bloodrequest', name='request_by_donor'),
        migrations.RemoveField(model_name='bloodrequest', name='request_by_patient'),
        migrations.RemoveField(model_name='bloodrequest', name='patient_name'),
        migrations.RemoveField(model_name='bloodrequest', name='patient_age'),
        migrations.RemoveField(model_name='bloodrequest', name='bloodgroup'),
        migrations.RemoveField(model_name='bloodrequest', name='unit'),
        migrations.RemoveField(model_name='bloodrequest', name='date'),

        # Step 3: Rename reason from CharField(500) to TextField
        migrations.AlterField(
            model_name='bloodrequest',
            name='reason',
            field=models.TextField(),
        ),

        # Step 4: Update status field with new choices and default
        migrations.AlterField(
            model_name='bloodrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('completed', 'Completed'),
                    ('rejected', 'Rejected'),
                    ('cancelled_by_user', 'Cancelled by User'),
                    ('cancelled_by_admin', 'Cancelled by Admin'),
                    ('expired', 'Expired'),
                ],
                default='pending',
                max_length=20,
            ),
        ),

        # Step 5: Add new fields — table is empty so defaults are cosmetic
        migrations.AddField(
            model_name='bloodrequest',
            name='patient',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='blood_requests',
                to='blood.PatientProfile',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='blood_type',
            field=models.CharField(
                choices=[('A', 'A'), ('B', 'B'), ('AB', 'AB'), ('O', 'O')],
                default='A',
                max_length=2,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='blood_sign',
            field=models.CharField(
                choices=[('+', '+'), ('-', '-')],
                default='+',
                max_length=1,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='units_needed',
            field=models.PositiveIntegerField(default=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='urgency',
            field=models.CharField(
                choices=[('normal', 'Normal'), ('urgent', 'Urgent'), ('critical', 'Critical')],
                default='normal',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='required_date',
            field=models.DateField(default='2026-01-01'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='recent_surgery',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='wilaya',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to='blood.Wilaya',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='commune',
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.PROTECT,
                to='blood.Commune',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default='2026-01-01T00:00:00Z'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
