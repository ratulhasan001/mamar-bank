from django.db import migrations


def create_default_bank(apps, schema_editor):
    Bank = apps.get_model('transactions', 'Bank')
    Bank.objects.get_or_create(name='mamar_bank')


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_bank_transfer'),
    ]

    operations = [
        migrations.RunPython(create_default_bank, migrations.RunPython.noop),
    ]
