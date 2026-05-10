from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("borghive", "0005_alter_alertpreference_id_alter_notification_id_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    "DROP TABLE IF EXISTS borghive_repositoryldapuser;",
                    reverse_sql="",
                ),
            ],
        ),
    ]
