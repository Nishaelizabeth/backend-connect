import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preferences', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the old unique constraint on name
        migrations.AlterField(
            model_name='interest',
            name='name',
            field=models.CharField(max_length=100),
        ),
        # Add is_default field
        migrations.AddField(
            model_name='interest',
            name='is_default',
            field=models.BooleanField(
                default=True,
                help_text='If True, this interest is visible to all users. If False, it is private to the user who created it.'
            ),
        ),
        # Add created_by ForeignKey
        migrations.AddField(
            model_name='interest',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                help_text='The user who created this interest. Null for default/global interests.',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='custom_interests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Add unique constraints
        migrations.AddConstraint(
            model_name='interest',
            constraint=models.UniqueConstraint(
                condition=models.Q(is_default=True),
                fields=['name'],
                name='unique_default_interest_name'
            ),
        ),
        migrations.AddConstraint(
            model_name='interest',
            constraint=models.UniqueConstraint(
                condition=models.Q(is_default=False),
                fields=['name', 'created_by'],
                name='unique_user_interest_name'
            ),
        ),
    ]
