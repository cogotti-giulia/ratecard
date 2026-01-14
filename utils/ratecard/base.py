import csv
from abc import ABCMeta, abstractmethod

from utils.style import Logger


# abstract class
class RateCardGenerator(object):
  __metaclass__ = ABCMeta

  def __init__(self, conn, origin_country, ratecard_fn, ratecard_table, surcharge_table):
    self._conn = conn
    self._origin_country = origin_country
    self._ratecard_table = ratecard_table
    self._surcharge_table = surcharge_table
    self._ratecard_fn = ratecard_fn
    self._logger = Logger()

  def _import_ratecard(self, clean_existing=True):
    self._logger.info("Importing {} into table {}".format(self._ratecard_fn, self._ratecard_table))
    data_to_insert = []

    with open(self._ratecard_fn, 'rb') as csv_file:
      reader = csv.reader(csv_file)
      for row in reader:
        data_to_insert.append((row[0], row[1], row[2]))

    if clean_existing:
      self._clean_db(self._ratecard_table)

    self._create_ratecard_table()

    with self._conn.cursor() as cursor:
      sql = "INSERT INTO {0} (dialprefix, destination, buyrate) VALUES (%s, %s, %s)".format(self._ratecard_table)
      cursor.executemany(sql, data_to_insert)
      self._logger.log(".....successfully inserted {0} records.".format(len(data_to_insert)))

  def _create_ratecard_table(self):

    self._logger.log("Creating {} table in the db...".format(self._ratecard_table))

    with self._conn.cursor() as cursor:
      sql = """CREATE TABLE IF NOT EXISTS {0} (
                  `dialprefix` bigint DEFAULT NULL,
                  `destination` text,
                  `buyrate` double DEFAULT NULL
                 ) ENGINE=MyISAM DEFAULT CHARSET=latin1;""".format(self._ratecard_table)
      cursor.execute(sql)


  def _create_surcharge_table(self):
    self._logger.log("Creating {} table in the db...".format(self._surcharge_table))

    with self._conn.cursor() as cursor:
      sql = """CREATE TABLE IF NOT EXISTS {} (
                 origin_name text,
                 origin_prefix bigint default NULL,
                 destination text,
                 surcharge_eur double default 0
               ) ENGINE=MyISAM DEFAULT CHARSET=latin1;""".format(self._surcharge_table)
      cursor.execute(sql)
      self._logger.log(".....done")

  def _clean_db(self, tables_to_clean):
    if not isinstance(tables_to_clean, list):
      tables_to_clean = [tables_to_clean]

    with self._conn.cursor() as cursor:
      for table_name in tables_to_clean:
        self._logger.log("Deleting {} table from the db...".format(self._surcharge_table))

        sql = """DROP TABLE IF EXISTS {0};""".format(table_name)
        cursor.execute(sql)
        self._logger.log(".....done")

  @abstractmethod
  def _import_surcharge(self, clean_existing=True):
    pass

  @abstractmethod
  def _apply_surcharge(self):
    pass


  def generate(self, clean_existing=True):
    try:
      if clean_existing:
        self._logger.warning("All existing records will be deleted.")
      # 1. ratecard
      self._import_ratecard(clean_existing)
      # 2. surcharge
      self._import_surcharge(clean_existing)
      self._apply_surcharge()

      # commit once if everything goes well
      self._conn.commit()
      self._logger.success("Everything worked as expected. Double check to be sure.")

    except Exception as e:
      self._conn.rollback()  # Undo everything if an error occurs
      self._logger.error("Error during generation. Rolled back changes.", error_detail=e)
      raise e
