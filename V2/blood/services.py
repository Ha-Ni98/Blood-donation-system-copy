from django.db import transaction
from django.utils.translation import gettext_lazy as _
from . import models


COMPATIBLE_BLOOD_TYPES = {
    'A+':  ['A+', 'A-', 'O+', 'O-'],
    'A-':  ['A-', 'O-'],
    'B+':  ['B+', 'B-', 'O+', 'O-'],
    'B-':  ['B-', 'O-'],
    'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
    'AB-': ['A-', 'B-', 'AB-', 'O-'],
    'O+':  ['O+', 'O-'],
    'O-':  ['O-'],
}


def get_compatible_blood_type_ids(blood_type):
    """Return IDs of BloodType instances compatible with the given blood type."""
    key = f"{blood_type.blood_type}{blood_type.blood_sign}"
    compatible_names = COMPATIBLE_BLOOD_TYPES.get(key, [key])
    ids = []
    for name in compatible_names:
        bt = name[:-1]
        sign = name[-1]
        ids.extend(
            models.BloodType.objects.filter(
                blood_type=bt, blood_sign=sign
            ).values_list('id', flat=True)
        )
    return ids


@transaction.atomic
def approve_blood_request(request_obj, attributions_data):
    """
    attributions_data: list of dicts with keys 'blood_type_id' and 'units_attributed'.
    Only entries with units_attributed > 0 are processed.
    """
    if request_obj.status != models.STATUS_PENDING:
        raise ValueError(_('Only pending requests can be approved.'))

    # Filter out zero/negative units
    attributions_data = [d for d in attributions_data if int(d['units_attributed']) > 0]

    if not attributions_data:
        raise ValueError(_('At least one blood type must have a positive quantity.'))

    compatible_ids = get_compatible_blood_type_ids(request_obj.blood_type)

    # Lock all relevant stocks
    blood_type_ids = [int(d['blood_type_id']) for d in attributions_data]
    stocks = {
        s.blood_type_id: s
        for s in models.BloodStock.objects.select_for_update().filter(
            blood_type_id__in=blood_type_ids
        )
    }

    created_attributions = []
    for data in attributions_data:
        bt_id = int(data['blood_type_id'])
        units = int(data['units_attributed'])

        if bt_id not in compatible_ids:
            raise ValueError(_('Selected blood type is not compatible with the requested blood type.'))

        stock = stocks.get(bt_id)
        if not stock:
            raise ValueError(_('No stock record found for the selected blood type.'))
        if stock.units_available < units:
            raise ValueError(_('Insufficient stock for blood type %(type)s.') % {'type': stock.blood_type})

        stock.units_available -= units
        stock.save()

        attribution = models.BloodAttribution.objects.create(
            blood_request=request_obj,
            blood_type_id=bt_id,
            units_attributed=units,
        )
        created_attributions.append(attribution)

    request_obj.status = models.STATUS_APPROVED
    request_obj.save()

    return created_attributions


@transaction.atomic
def complete_blood_request(request_obj, attributions_data):
    if request_obj.status != models.STATUS_APPROVED:
        raise ValueError(_('Only approved requests can be completed.'))

    blood_type_ids = [d['blood_type_id'] for d in attributions_data]
    stocks = {
        s.blood_type_id: s
        for s in models.BloodStock.objects.select_for_update().filter(
            blood_type_id__in=blood_type_ids
        )
    }

    existing_attributions = {
        a.blood_type_id: a
        for a in request_obj.attributions.all()
    }

    for data in attributions_data:
        bt_id = int(data['blood_type_id'])
        new_units = int(data['units_attributed'])
        if new_units < 0:
            raise ValueError(_('Units attributed cannot be negative.'))

        stock = stocks.get(bt_id)
        if not stock:
            raise ValueError(_('No stock record found for the selected blood type.'))

        existing = existing_attributions.get(bt_id)
        if existing:
            delta = new_units - existing.units_attributed
            if delta > 0:
                if stock.units_available < delta:
                    raise ValueError(_('Insufficient stock to increase attribution.'))
                stock.units_available -= delta
                stock.save()
            elif delta < 0:
                stock.units_available += abs(delta)
                stock.save()
            existing.units_attributed = new_units
            existing.save()
        else:
            if stock.units_available < new_units:
                raise ValueError(_('Insufficient stock for this blood type.'))
            stock.units_available -= new_units
            stock.save()
            models.BloodAttribution.objects.create(
                blood_request=request_obj,
                blood_type_id=bt_id,
                units_attributed=new_units,
            )

    for bt_id, attr in existing_attributions.items():
        if bt_id not in [int(d['blood_type_id']) for d in attributions_data]:
            stock = stocks.get(bt_id)
            if stock:
                stock.units_available += attr.units_attributed
                stock.save()
            attr.delete()

    request_obj.status = models.STATUS_COMPLETED
    request_obj.save()


@transaction.atomic
def reject_blood_request(request_obj):
    if request_obj.status not in (models.STATUS_PENDING, models.STATUS_APPROVED):
        raise ValueError(_('Only pending or approved requests can be rejected.'))

    if request_obj.status == models.STATUS_APPROVED:
        for attr in list(request_obj.attributions.all()):
            stock = models.BloodStock.objects.select_for_update().filter(
                blood_type=attr.blood_type
            ).first()
            if stock:
                stock.units_available += attr.units_attributed
                stock.save()
            attr.delete()

    request_obj.status = models.STATUS_CANCELLED_BY_ADMIN
    request_obj.save()


@transaction.atomic
def cancel_blood_request_by_user(request_obj):
    if request_obj.status not in (models.STATUS_PENDING, models.STATUS_APPROVED):
        raise ValueError(_('Only pending or approved requests can be cancelled.'))

    if request_obj.status == models.STATUS_APPROVED:
        for attr in list(request_obj.attributions.all()):
            stock = models.BloodStock.objects.select_for_update().filter(
                blood_type=attr.blood_type
            ).first()
            if stock:
                stock.units_available += attr.units_attributed
                stock.save()
            attr.delete()

    request_obj.status = models.STATUS_CANCELLED_BY_USER
    request_obj.save()
