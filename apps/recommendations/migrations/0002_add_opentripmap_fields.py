# Generated manually for OpenTripMap integration

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0001_initial'),
    ]

    operations = [
        # Add xid field for OpenTripMap identifier
        migrations.AddField(
            model_name='destination',
            name='xid',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        # Add coordinates
        migrations.AddField(
            model_name='destination',
            name='lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='destination',
            name='lon',
            field=models.FloatField(blank=True, null=True),
        ),
        # Add kinds for OpenTripMap tags
        migrations.AddField(
            model_name='destination',
            name='kinds',
            field=models.CharField(blank=True, default='', help_text='OpenTripMap kinds/tags', max_length=500),
        ),
        # Add timestamps
        migrations.AddField(
            model_name='destination',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='destination',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # Make country and description optional with defaults
        migrations.AlterField(
            model_name='destination',
            name='country',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='destination',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        # Add order and notes to TripSavedDestination
        migrations.AddField(
            model_name='tripsaveddestination',
            name='order',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tripsaveddestination',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
