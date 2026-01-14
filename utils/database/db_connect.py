import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

from utils.database.db_config import ratecard_db_config
from utils.style import Logger


@contextmanager
def get_db_connection():
  logger = Logger()
  conn = None
  try:
    # 1. SETUP: Connect to DB
    conn = mysql.connector.connect(**ratecard_db_config)

    # 2. YIELD: Give control back to the main script
    yield conn

  except Error as e:
    logger.error("Database error", error_detail=e)
    # Optional: Raise the error again if you want the main script to crash
    # raise e

  finally:
    # 3. TEARDOWN: This runs no matter what happens (even on errors)
    if conn and conn.is_connected():
      conn.close()
      logger.log("Database connection closed")

from contextlib import contextmanager

@contextmanager
def get_connection_cursor(conn, commit=False):
  """
  Context manager for a MySQL cursor (Python 2.7 safe).

  Args:
      conn: MySQL connection
      commit: if True, commits changes on exit
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

