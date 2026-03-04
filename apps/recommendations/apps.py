from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.recommendations'
    
    def ready(self):
        """Import signals when app is ready and reset stale pending caches on startup."""
        import apps.recommendations.signals  # noqa

        # Use connection_created signal to defer DB access until a connection exists.
        # This avoids the RuntimeWarning while still running on every server start.
        from django.db.backends.signals import connection_created
        connection_created.connect(_reset_stale_pending_caches_once)


_reset_done = False


def _reset_stale_pending_caches_once(sender, connection, **kwargs):
    """
    Reset PENDING caches to FAILED on the first DB connection after server start.
    This handles caches orphaned when the auto-reloader kills background threads.
    Runs once per process via the _reset_done guard.
    """
    global _reset_done
    if _reset_done:
        return
    _reset_done = True
    try:
        from apps.recommendations.models import TripRecommendationCache
        stale = TripRecommendationCache.objects.filter(
            status=TripRecommendationCache.Status.PENDING
        )
        count = stale.count()
        if count:
            stale.update(status=TripRecommendationCache.Status.FAILED)
            print(f"[STARTUP] Reset {count} stale PENDING recommendation cache(s) to FAILED")
    except Exception:
        pass
