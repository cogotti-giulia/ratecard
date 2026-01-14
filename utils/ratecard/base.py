import time
from abc import ABCMeta, abstractmethod

from utils.style import Logger


# abstract class
class RateCardGenerationService(object):
  __metaclass__ = ABCMeta

  def __init__(self, conn, origin_country, ratecard_fn, ratecard_table, surcharge_table, dialprefix_idx):
    self._conn = conn
    self._origin_country = origin_country
    self._ratecard_table = ratecard_table
    self._surcharge_table = surcharge_table
    self._ratecard_fn = ratecard_fn
    self._dialprefix_idx = dialprefix_idx
    self._logger = Logger()

  def _create_and_populate_ratecard(self, clean_existing=True):
    """
    Drops ratecard table if it exists.
    Creates ratecard table if it doesn't exist, adding an index on dialprefix to speedup any further operations.
    Loads csv supplier data into the ratecard table, using the sql LOAD DATA LOCAL INFILE to speedup the proccess.
    :param clean_existing:
    :return:
    """
    start = time.time()
    self._logger.info("Importing {} into table {}".format(self._ratecard_fn, self._ratecard_table))
    data_to_insert = []

    # with open(self._ratecard_fn, 'rb') as csv_file:
    #   reader = csv.reader(csv_file)
    #   for row in reader:
    #     data_to_insert.append((row[0], row[1], row[2]))

    if clean_existing:
      self._drop_existing_tables(self._ratecard_table)

    self._create_ratecard_table_with_index()

    with self._conn.cursor() as cursor:
      # sql = "INSERT INTO {0} (dialprefix, destination, buyrate) VALUES (%s, %s, %s)".format(self._ratecard_table)
      # cursor.executemany(sql, data_to_insert)
      sql = """
        LOAD DATA LOCAL INFILE %s
        INTO TABLE {ratecard_table}
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\n'
      """.format(ratecard_table=self._ratecard_table)
      cursor.execute(sql, (self._ratecard_fn,))
      end = time.time()
      self._logger.log(".....successfully inserted {0} records in {1:.4f}s.".format(len(data_to_insert), end - start))

  def _create_ratecard_table_with_index(self):
    """
    Creates ratecard table if it doesn't exist, adding an index on dialprefix to speedup any further operations.
    """

    self._logger.log("Creating {} table in the db (and index on dialprefix)...".format(self._ratecard_table))

    with self._conn.cursor() as cursor:
      sql = """CREATE TABLE IF NOT EXISTS {0} (
                  `dialprefix` bigint DEFAULT NULL,
                  `destination` text,
                  `buyrate` double DEFAULT NULL
                 ) ENGINE=MyISAM DEFAULT CHARSET=latin1;""".format(self._ratecard_table)
      cursor.execute(sql)
      # create idx on created table dialprefix
      sql = """
      CREATE INDEX {0} ON {1} (dialprefix)
      """.format(self._dialprefix_idx, self._ratecard_table)
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

  def _drop_existing_tables(self, tables_to_clean):
    if not isinstance(tables_to_clean, list):
      tables_to_clean = [tables_to_clean]

    with self._conn.cursor() as cursor:
      for table_name in tables_to_clean:
        self._logger.log("Deleting {} table from the db...".format(table_name))
        sql = """DROP TABLE IF EXISTS {0};""".format(table_name)
        cursor.execute(sql)
        self._logger.log(".....done")

  @abstractmethod
  def _load_surcharge_data(self, clean_existing=True):
    """
    Loads surcharge data into a surcharge table, subclasses must implement this method (cause it depends on surcharge
    files provided by the specific supplier).
    """
    pass

  @abstractmethod
  def _apply_surcharge_to_ratecard(self):
    """
    Applies surcharge to ratecard table.
    :return:
    """
    pass

  def generate(self, clean_existing=True):
    """
    Clears all existing records (dropping tables).
    Creates and populates ratecard table from supplier csv ratecard data.
    Loads surcharge into a surcharge table from supplier surcharge xlxs file data.
    Applies the surcharge based on origin country.

    Commits db changes only if everything goes well, otherwise rollbacks and raises an error.

    :param clean_existing: True to start from an empty db.
    """
    try:
      if clean_existing:
        self._logger.warning("All existing records will be deleted.")
      # 1. ratecard
      self._create_and_populate_ratecard(clean_existing)
      # 2. surcharge
      self._load_surcharge_data(clean_existing)
      self._apply_surcharge_to_ratecard()

      # commit once if everything goes well
      self._conn.commit()
      self._logger.success("Everything worked as expected. Double check to be sure.")

    except Exception as e:
      self._conn.rollback()  # Undo everything if an error occurs
      self._logger.error("Error during generation. Rolled back changes.", error_detail=e)
      raise
