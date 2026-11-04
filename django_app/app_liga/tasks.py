from celery import shared_task


@shared_task
def finalize_expired_attempts_task():
    from . import services
    return services.finalize_expired()


@shared_task
def close_finished_seasons_task():
    from . import services
    return services.close_finished_seasons()
