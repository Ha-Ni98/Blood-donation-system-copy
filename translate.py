import polib
import os

from collections import defaultdict

fr_translations = {
    'Requests Dashboard': 'Tableau de bord des demandes',
    'Filter': 'Filtrer',
    'Status': 'Statut',
    'Blood Type': 'Groupe Sanguin',
    'Blood Sign': 'Signe Sanguin',
    'Urgency': 'Urgence',
    'Wilaya': 'Wilaya',
    'Apply Filters': 'Appliquer les filtres',
    'Reset': 'Réinitialiser',
    'Blood Requests': 'Demandes de Sang',
    'Request ID': 'ID Demande',
    'Patient Name': 'Nom du Patient',
    'Created At': 'Créé le',
    'Actions': 'Actions',
    'Critical': 'Critique',
    'Urgent': 'Urgent',
    'Normal': 'Normal',
    'Approve': 'Approuver',
    'Reject': 'Rejeter',
    'Cancel': 'Annuler',
    'Complete': 'Terminer',
    'No blood requests found.': 'Aucune demande de sang trouvée.',
    'Donation Requests': 'Demandes de Don',
    'Filter Donations:': 'Filtrer les dons :',
    'Donor Name': 'Nom du Donneur',
    'No donation requests found.': 'Aucune demande de don trouvée.',
    'User Management': 'Gestion des utilisateurs',
    'Registered Users': 'Utilisateurs Enregistrés',
    'NIN': 'NIN',
    'Name': 'Nom',
    'Date Joined': 'Date d\'inscription',
    'Action': 'Action',
    'Active': 'Actif',
    'Inactive': 'Inactif',
    'Deactivate': 'Désactiver',
    'Activate': 'Activer',
    'Are you sure you want to change this user\\\'s status?': 'Êtes-vous sûr de vouloir modifier le statut de cet utilisateur ?',
    'No users found in the system.': 'Aucun utilisateur trouvé dans le système.',
    'Donor Eligibility': 'Éligibilité des Donneurs',
    'Registered Donors': 'Donneurs Enregistrés',
    'Last Donation': 'Dernier Don',
    'Eligibility': 'Éligibilité',
    'Never': 'Jamais',
    'Eligible': 'Éligible',
    'Ineligible': 'Non Éligible',
    'Mark Ineligible': 'Marquer Non Éligible',
    'Mark Eligible': 'Marquer Éligible',
    'Are you sure you want to change this donor\\\'s eligibility?': 'Êtes-vous sûr de vouloir modifier l\'éligibilité de ce donneur ?',
    'No donors found in the system.': 'Aucun donneur trouvé dans le système.',
    'Approve Blood Request': 'Approuver la Demande de Sang',
    'Select Donor': 'Sélectionner le Donneur',
    'Select': 'Sélectionner',
    'Confirm Approval': 'Confirmer l\'Approbation',
    'No eligible donors available for this blood type.': 'Aucun donneur éligible disponible pour ce groupe sanguin.',
    'There are no pending donation requests matching': 'Il n\'y a aucune demande de don en attente correspondant à',
    'Return to Dashboard': 'Retourner au Tableau de Bord',
    'Approve Donation Request': 'Approuver la Demande de Don',
    'Select Blood Request': 'Sélectionner une Demande de Sang',
    'No eligible blood requests available for this blood type.': 'Aucune demande de sang éligible disponible pour ce groupe sanguin.',
    'There are no pending blood requests matching': 'Il n\'y a aucune demande de sang en attente correspondant à'
}

ar_translations = {
    'Requests Dashboard': 'لوحة تحكم الطلبات',
    'Filter': 'تصفية',
    'Status': 'الحالة',
    'Blood Type': 'فصيلة الدم',
    'Blood Sign': 'إشارة الدم',
    'Urgency': 'الاستعجال',
    'Wilaya': 'الولاية',
    'Apply Filters': 'تطبيق عوامل التصفية',
    'Reset': 'إعادة تعيين',
    'Blood Requests': 'طلبات الدم',
    'Request ID': 'معرف الطلب',
    'Patient Name': 'اسم المريض',
    'Created At': 'تاريخ الإنشاء',
    'Actions': 'إجراءات',
    'Critical': 'حرج',
    'Urgent': 'عاجل',
    'Normal': 'عادي',
    'Approve': 'موافقة',
    'Reject': 'رفض',
    'Cancel': 'إلغاء',
    'Complete': 'إكمال',
    'No blood requests found.': 'لم يتم العثور على طلبات دم.',
    'Donation Requests': 'طلبات التبرع',
    'Filter Donations:': 'تصفية التبرعات:',
    'Donor Name': 'اسم المتبرع',
    'No donation requests found.': 'لم يتم العثور على طلبات تبرع.',
    'User Management': 'إدارة المستخدمين',
    'Registered Users': 'المستخدمون المسجلون',
    'NIN': 'رقم التعريف الوطني',
    'Name': 'الاسم',
    'Date Joined': 'تاريخ الانضمام',
    'Action': 'إجراء',
    'Active': 'نشط',
    'Inactive': 'غير نشط',
    'Deactivate': 'تعطيل',
    'Activate': 'تفعيل',
    'Are you sure you want to change this user\\\'s status?': 'هل أنت متأكد أنك تريد تغيير حالة هذا المستخدم؟',
    'No users found in the system.': 'لم يتم العثور على مستخدمين في النظام.',
    'Donor Eligibility': 'أهلية المتبرعين',
    'Registered Donors': 'المتبرعين المسجلين',
    'Last Donation': 'آخر تبرع',
    'Eligibility': 'الأهلية',
    'Never': 'أبدا',
    'Eligible': 'مؤهل',
    'Ineligible': 'غير مؤهل',
    'Mark Ineligible': 'جعله غير مؤهل',
    'Mark Eligible': 'جعله مؤهل',
    'Are you sure you want to change this donor\\\'s eligibility?': 'هل أنت متأكد أنك تريد تغيير أهلية هذا المتبرع؟',
    'No donors found in the system.': 'لم يتم العثور على متبرعين في النظام.',
    'Approve Blood Request': 'الموافقة على طلب الدم',
    'Select Donor': 'حدد المتبرع',
    'Select': 'تحديد',
    'Confirm Approval': 'تأكيد الموافقة',
    'No eligible donors available for this blood type.': 'لا يتوفر متبرعون مؤهلون لفصيلة الدم هذه.',
    'There are no pending donation requests matching': 'لا توجد طلبات تبرع معلقة مطابقة',
    'Return to Dashboard': 'العودة إلى لوحة القيادة',
    'Approve Donation Request': 'الموافقة على طلب التبرع',
    'Select Blood Request': 'حدد طلب الدم',
    'No eligible blood requests available for this blood type.': 'لا تتوفر طلبات دم مؤهلة لفصيلة الدم هذه.',
    'There are no pending blood requests matching': 'لا توجد طلبات دم معلقة مطابقة'
}

def translate_po(file_path, translations_dict):
    po = polib.pofile(file_path)
    count = 0
    for entry in po:
        if not entry.msgstr and entry.msgid in translations_dict:
            entry.msgstr = translations_dict[entry.msgid]
            count += 1
    po.save()
    print(f"Updated {count} empty translations in {file_path}")

fr_po = '/home/johndoe/Project/blood-bank-managment-system/locale/fr/LC_MESSAGES/django.po'
ar_po = '/home/johndoe/Project/blood-bank-managment-system/locale/ar/LC_MESSAGES/django.po'

translate_po(fr_po, fr_translations)
translate_po(ar_po, ar_translations)

print("Translation script complete.")
