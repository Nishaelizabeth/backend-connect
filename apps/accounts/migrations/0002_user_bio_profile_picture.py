from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(blank=True, default='', help_text='Short biography or description of the user.', verbose_name='Bio'),
        ),
        migrations.AddField(
            model_name='user',
            name='profile_picture',
            field=models.ImageField(blank=True, help_text='Uploaded profile photo.', null=True, upload_to='profile_pictures/', verbose_name='Profile Picture'),
        ),
        migrations.AddField(
            model_name='user',
            name='google_picture_url',
            field=models.URLField(blank=True, help_text='Profile picture URL from Google OAuth.', max_length=500, null=True, verbose_name='Google Picture URL'),
        ),
    ]
