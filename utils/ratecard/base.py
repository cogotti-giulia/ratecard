import time
from abc import ABCMeta, abstractmethod

from utils.database.sql import SqlHelper
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
    self._sql_helper = SqlHelper(conn)
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

    if clean_existing:
      self._sql_helper.drop_tables(self._ratecard_table)

    self._create_ratecard_table_with_index()

    with self._conn.cursor() as cursor:
      sql = """
        LOAD DATA LOCAL INFILE %s
        INTO TABLE {ratecard_table}
        FIELDS TERMINATED BY ','
        ENCLOSED BY '"'
        LINES TERMINATED BY '\n'
      """.format(ratecard_table=self._ratecard_table)
      cursor.execute(sql, (self._ratecard_fn,))
      end = time.time()
      self._logger.log(".....successfully inserted {0} records in {1:.4f}s.".format(cursor.rowcount, end - start))

  def _create_ratecard_table_with_index(self):
    """
    Creates ratecard table if it doesn't exist, adding an index on dialprefix to speedup any further operations.
    """
    self._sql_helper.create_table(
      self._ratecard_table,
      columns=[("dialprefix", "bigint", "DEFAULT NULL"),
        ("destination", "text", ""),
        ("buyrate", "double", "DEFAULT NULL")
       ]
    )
    self._sql_helper.create_index(idx=self._dialprefix_idx, table=self._ratecard_table, column="dialprefix")

  def _create_surcharge_table(self):
    columns = [
      ("origin_name", "text", ""),
      ("origin_prefix", "bigint", "DEFAULT NULL"),
      ("destination", "text", ""),
      ("surcharge_eur", "double", "DEFAULT 0"),
    ]

    self._sql_helper.create_table(self._surcharge_table, columns=columns)

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
