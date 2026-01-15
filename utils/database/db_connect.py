import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

from utils.database.db_config import ratecard_db_config
from utils.style import Logger


@contextmanager
def get_db_connection():
  """
  Context manager that creates a database connection.
  Whatever happens it happens, but at the end it closes the connection (even in case of errors).
  :return:
  """
  logger = Logger()
  conn = None
  try:
    # connect to DB
    conn = mysql.connector.connect(**ratecard_db_config)

    # give control back to the main script
    yield conn

  except Error as e:
    logger.error("Database error", error_detail=e)
    # Optional: Raise the error again if you want the main script to crash
    raise e

  finally:
    # this runs no matter what happens (even on errors)
    if conn and conn.is_connected():
      conn.close()
      logger.log("Database connection closed")

from contextlib import contextmanager

@contextmanager
def get_connection_cursor(conn, commit=False):
  """
  Context manager for a MySQL cursor.
  Whatever happens it happens, but at the end it closes the cursor (even in case of errors).

  :param conn: MySQL connection
  :param commit: if True, commits changes on exit
  """
  cursor = conn.cursor()
  try:
    yield cursor
    if commit:
      conn.commit()
  except Exception:
    conn.rollback()
    raise
  finally:
    # In Python 2.7, explicitly consume any remaining rows to prevent "Unread result"
    try:
      while cursor.nextset():
        pass
    except:
      pass
    cursor.close()

