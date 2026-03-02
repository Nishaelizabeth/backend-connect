from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recommendations'
    
    def ready(self):
        """Import signals when app is ready."""
        import apps.recommendations.signals  # noqa
