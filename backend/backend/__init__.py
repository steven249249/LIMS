# Register PyMySQL as the `MySQLdb` driver Django expects when using the
# mysql backend. Pure-Python so we don't have to compile mysqlclient against
# libmysqlclient at image-build time. This must run before Django imports
# its database layer, which means right at the top of the project package.
import pymysql

pymysql.install_as_MySQLdb()

# This ensures Celery app is loaded when Django starts.
from .celery import app as celery_app  # noqa: E402

__all__ = ['celery_app']
