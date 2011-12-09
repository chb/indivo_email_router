"""
.. module:: celeryconfig
   :synopsis: Configuration settings for celery

.. moduleauthor:: Daniel Haas <daniel.haas@post.harvard.edu>

"""
from datetime import timedelta
import settings

# Configuration for celerybeat, the cron-like task scheduler
CELERYBEAT_SCHEDULE = {
    "poll_mailbox": {
        "task": "tasks.get_new_emails",
        "schedule":timedelta(seconds=settings.EMAIL_POLL_INTERVAL),
        },
}

# Configuration for the RabbitMQ broker
BROKER_TRANSPORT = "amqplib"
BROKER_HOST = "localhost"
BROKER_PORT = "5672"
BROKER_USER = settings.RABBITMQ_USER
BROKER_PASSWORD = settings.RABBITMQ_PASSWORD
BROKER_VHOST = settings.RABBITMQ_VHOST

# Configuration for results
CELERY_RESULT_BACKEND = "amqp" # Where to store task results
CELERY_TASK_RESULT_EXPIRES = 18000 # Number of seconds before a task result expires (5 hours here)

# Configuration for notifications
CELERY_SEND_TASK_ERROR_EMAILS = settings.SEND_MAIL
ADMINS = settings.ADMINS
SERVER_EMAIL = settings.SERVER_EMAIL
EMAIL_HOST = settings.EMAIL_HOST
EMAIL_PORT = settings.EMAIL_PORT
EMAIL_HOST_USER = settings.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD
EMAIL_USE_SSL = settings.EMAIL_USE_SSL
EMAIL_USE_TLS = settings.EMAIL_USE_TLS

# General Celery configuration
CELERY_IMPORTS = ("tasks",) # Which modules to find tasks in
CELERY_DISABLE_RATE_LIMITS = True
