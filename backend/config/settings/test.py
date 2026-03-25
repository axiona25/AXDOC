"""Settings per pytest: Celery esegue i task in-process."""
from .development import *

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
