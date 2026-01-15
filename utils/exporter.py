import csv
import datetime
import os

import pandas as pd
from utils.config import STATIC_DOC_ROOT
from utils.database.sql import SqlHelper
from utils.style import Logger


class BaseExporter(object):
  """
  Pandas exporter helper to make easier the exports, so your brain shouldn't remember how to write those lines every time :)
  P.S.: every export will be saved under the folder export/<year>/<month>/<filename>.<extension> in the STATIC_DOC_ROOT
  """
  SEPARATOR = '/'
  YEAR = '%Y'
  MONTH = '%m'
  DAY = '%d'

  def __init__(self, filename):
    self.filename = filename
    self._logger = Logger()

  def _compose_export_file_path(self ,filename, extension='txt'):
    date_path = datetime.date.today().strftime(self.SEPARATOR + self.YEAR + self.SEPARATOR + self.MONTH + self.SEPARATOR + self.DAY + self.SEPARATOR)

    folder = 'export'
    return folder + date_path + filename + '.' + extension

  def _compose_path(self, extension='txt'):
    filepath = os.path.join(STATIC_DOC_ROOT, self._compose_export_file_path(self.filename, extension))

    if not os.path.exists(os.path.dirname(filepath)):
      os.makedirs(os.path.dirname(filepath))

    return filepath

class BaseSqlExporter(BaseExporter):
  def __init__(self, conn, query, filename):
    self._conn = conn
    self._query = query
    self._sql_helper = SqlHelper(conn)

    super(BaseSqlExporter, self).__init__(filename)

  def to_csv(self):
    filepath = self._compose_path(extension='csv')
    def save_to_file(cursor):
      with open(filepath, "wb") as f:
        writer = csv.writer(f)
        # -- NO HEADER
        while True:
          rows = cursor.fetchmany(1000)
          if not rows:
            break

          for row in rows:
            writer.writerow([
              item.encode("utf-8") if isinstance(item, unicode) else item
              for item in row
            ])

    self._sql_helper.execute(self._query, func=save_to_file)
    self._logger.info("Exported data into {}".format(filepath))
    return filepath
