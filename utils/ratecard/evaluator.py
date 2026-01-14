
from utils.config import RATECARD_CONFIG
from utils.style import Logger


# pesi

# creare nuova colonna nelle merged chiamata boh `weight`

class RatecardRouteEvaluator(object):
  PRIMARY_ROUTE_WEIGHT = 0.1
  SECONDARY_ROUTE_WEIGHT = 0.3

  def __init__(self, conn, origin_country_code):
    self._conn = conn
    self._origin_country_code = origin_country_code
    self._logger = Logger()
  #
  # def _create_index(self, table_name):
  #   cursor = self._conn.cursor()
  #   index_name = "{}_IDX".format(table_name)
  #   sql = """CREATE INDEX IF NOT EXISTS {0} ON {1} (dialprefix)""".format(index_name, table_name)
  #   cursor.execute(sql)
  #
  # def _drop_index(self, table_name, index_name):

  def _add_column_weight(self, table_name):
    cursor = self._conn.cursor()
    sql = """ALTER TABLE {0} ADD `weight` double DEFAULT NULL""".format(table_name)
    cursor.execute(sql)

  def _assign_weights_by_buyrate(self, base_table, competitor_table):
    cursor = self._conn.cursor()
    sql = """
      UPDATE {base_table} base
        JOIN {competitor_table} competitor
        ON base.dialprefix = competitor.dialprefix 
      SET base.weight = CASE
        WHEN base.buyrate <= competitor.buyrate THEN {wight_good}
        ELSE {wight_bad}
        END
    """.format(
      base_table=base_table,
      competitor_table=competitor_table,
      wight_good=self.PRIMARY_ROUTE_WEIGHT,
      wight_bad=self.SECONDARY_ROUTE_WEIGHT
    )
    cursor.execute(sql)

  def assign_route_weights(self, base_supplier, comparison_supplier):
    base_merged_tb = RATECARD_CONFIG[base_supplier]['merged_table'].format(
      origin_country_code=self._origin_country_code)
    comparison_merged_tb = RATECARD_CONFIG[comparison_supplier]['merged_table'].format(
      origin_country_code=self._origin_country_code)
    try:
      self._add_column_weight(base_merged_tb)
      # self._create_index(base_merged_tb)
      self._assign_weights_by_buyrate(base_merged_tb, comparison_merged_tb)

    except Exception as e:
      self._conn.rollback()  # Undo everything if an error occurs
      self._logger.error("Error during evaluation. Rolled back changes.", error_detail=e)
      raise e

