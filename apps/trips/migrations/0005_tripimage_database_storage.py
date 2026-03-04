from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0004_tripimage'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tripimage',
            name='image',
        ),
        migrations.AddField(
            model_name='tripimage',
            name='image_data',
            field=models.TextField(blank=True, default='', help_text='Base64-encoded image bytes'),
        ),
        migrations.AddField(
            model_name='tripimage',
            name='content_type',
            field=models.CharField(blank=True, default='image/jpeg', help_text='MIME type of the image', max_length=50),
        ),
    ]
