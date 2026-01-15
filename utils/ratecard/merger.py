import time

from utils.config import RATECARD_CONFIG
from utils.costants import COUNTRY_CODE_NAME_MAP
from utils.database.db_connect import get_connection_cursor
from utils.database.sql import SqlHelper
from utils.style import Logger

from tabulate import tabulate


class SupplierRateCardMerger(object):
  """Responsible for merging two supplier ratecards (a base supplier and a fallback supplier)
  into a single merged ratecard table. To cover all dialprefix destinations for the base supplier.
  """

  def __init__(self, conn, origin_country_code):
    self._conn = conn
    self._origin_country_code = origin_country_code
    self._sql_helper = SqlHelper(conn)
    self._logger = Logger()

  def _warn_on_missing_buyrates(self, base_supplier):
    """
    Warns for missing base rating tears (no buyrate) in the merged ratecard
    :param base_supplier:
    """
    with get_connection_cursor(self._conn) as cursor:
      sql = """
      SELECT * from {0} 
      where buyrate is null; """.format(
        RATECARD_CONFIG[base_supplier]['merged_table'].format(origin_country_code=self._origin_country_code))

      cursor.execute(sql)

      rows = cursor.fetchall()  # tuple of rows
      headers = [desc[0] for desc in cursor.description]  # column names

      self._logger.warning(
        "Missing base rating tiers in '{0}'.\nMake sure to add a buyrate for them in the {1}. Check the details below.".format(
          RATECARD_CONFIG[base_supplier]['ratecard_table'].format(origin_country_code=self._origin_country_code),
          RATECARD_CONFIG[base_supplier]['merged_table'].format(origin_country_code=self._origin_country_code)
        ), warning_detail='\n' + tabulate(rows, headers=headers, tablefmt='grid', showindex=False))

  def _build_merged_ratecard_and_add_dialprefix_index(self, base_supplier, fallback_supplier):
    """
    Creates the merged ratecard table for base_supplier

    Merges data using the following rules:
    1. For each fallback prefix, finds the longest matching base prefix
    2. Uses base destination and buyrate when matched
    3. Uses fallback destination otherwise
    4. Adds all base-only prefixes that do not exist in fallback
    5. Creates an index on dialprefix for performance

    :param base_supplier:
    :param fallback_supplier:
    :return:
    """
    with get_connection_cursor(self._conn, commit=True) as cursor:
      start = time.time()

      merged_table = RATECARD_CONFIG[base_supplier]['merged_table'].format(
        origin_country_code=self._origin_country_code)
      sql = """
        CREATE TABLE {merged_table} AS
         SELECT fallback.dialprefix, 
                  CASE 
                    WHEN base.dialprefix=fallback.dialprefix THEN base.destination 
                    ELSE fallback.destination 
                  END AS destination,
                  base.buyrate
         FROM {fallback_supplier} fallback
         LEFT JOIN (
           -- quanto e lungo il miglior (piu lungo) prefisso COLT per ogni prefisso TWT 
             SELECT 
                 fallback_inner.dialprefix, 
                 MAX(LENGTH(base_inner.dialprefix)) as max_len
             FROM {fallback_supplier} fallback_inner
             JOIN {base_supplier} base_inner 
               ON fallback_inner.dialprefix LIKE CONCAT(base_inner.dialprefix, '%')
             GROUP BY fallback_inner.dialprefix
         ) max_table
           ON fallback.dialprefix = max_table.dialprefix 
         -- prende il prefisso migliore
         LEFT JOIN {base_supplier} base
           ON fallback.dialprefix LIKE CONCAT(base.dialprefix, '%') 
           AND LENGTH(base.dialprefix) = max_table.max_len
            UNION ALL
            -- tutto quello, evidando duplicati, presente nella base ma non nell'altra
          SELECT base_no_match.dialprefix, base_no_match.destination, base_no_match.buyrate
            from {base_supplier} base_no_match 
            where base_no_match.dialprefix NOT IN (
            SELECT fallback_no_match.dialprefix
            from {fallback_supplier} fallback_no_match);
         """.format(
        merged_table=merged_table,
        base_supplier=RATECARD_CONFIG[base_supplier]['ratecard_table'].format(
          origin_country_code=self._origin_country_code),
        fallback_supplier=RATECARD_CONFIG[fallback_supplier]['ratecard_table'].format(
          origin_country_code=self._origin_country_code),
      )
      cursor.execute(sql)
      end = time.time()

      self._sql_helper.create_index(
        idx=RATECARD_CONFIG[base_supplier]['dialprefix_idx'].format(origin_country_code=self._origin_country_code),
        table=merged_table,
        column="dialprefix"
      )

      self._logger.log(
        "...succesfullty inserted {} into table {} in {:.4f}s".format(cursor.rowcount, RATECARD_CONFIG[base_supplier][
          'merged_table'].format(origin_country_code=self._origin_country_code), end - start))

  def merge_into_base(self, base_supplier, fallback_supplier, clean_existing=True):
    """
    main entry point for merging ratecards
    :param base_supplier: base supplier name
    :param fallback_supplier: fallback supplier name
    :param clean_existing: if True, removes existing tables
    """
    try:
      if clean_existing:
        self._logger.warning("All existing records will be deleted.")
        merged_table_table = RATECARD_CONFIG[base_supplier]['merged_table'].format(
          origin_country_code=self._origin_country_code)
        self._sql_helper.drop_tables(merged_table_table)

      self._logger.info(
        "***** MERGING {fallback_supplier} ratecard into {base_supplier} ratecard - {country_name} *****".format(
          fallback_supplier=fallback_supplier,
          base_supplier=base_supplier,
          country_name=COUNTRY_CODE_NAME_MAP[self._origin_country_code]
        ))

      self._build_merged_ratecard_and_add_dialprefix_index(base_supplier, fallback_supplier)
      self._conn.commit()

      self._warn_on_missing_buyrates(base_supplier)
      self._logger.success("Everything worked as expected. Double check to be sure.")

    except Exception as e:
      self._conn.rollback()  # Undo everything if an error occurs
      self._logger.error("Error during generation. Rolled back changes.", error_detail=e)
      raise
