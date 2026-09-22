from django.core.management import call_command
from django.db import migrations


def create_cache_table(apps, schema_editor):
    call_command("createcachetable")


def drop_cache_table(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS django_cache")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_remove_village_unique_village_name_per_company_and_more"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, drop_cache_table),
    ]
