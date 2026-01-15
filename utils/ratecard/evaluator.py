from utils.config import RATECARD_CONFIG
from utils.costants import COUNTRY_CODE_NAME_MAP
from utils.database.sql import SqlHelper
from utils.style import Logger


class RatecardRouteEvaluator(object):
  """
  Assigns route weight to the base supplier (primary or secondary) based on the comparison of the buyprice of the merged ratecards
  between base_supplier and comparison_supplier
  """
  PRIMARY_ROUTE_WEIGHT = 0.1
  SECONDARY_ROUTE_WEIGHT = 0.3

  def __init__(self, conn, origin_country_code):
    self._conn = conn
    self._origin_country_code = origin_country_code
    self._sql_helper = SqlHelper(conn)
    self._logger = Logger()

  def _add_column_weight(self, base_table):
    """
    Adds a column weight to the table.
    :param base_table:
    :return:
    """
    query = """ALTER TABLE {0} ADD `weight` double DEFAULT NULL""".format(base_table)
    self._sql_helper.execute(query)

  def _assign_weights_by_buyrate(self, base_table, competitor_table):
    """
    Calculates weights based on the comparison of buyrates from base and competitor tables and saves in the
    weight column of the base table.
    :param base_table:
    :param competitor_table:
    :return:
    """
    query = """
      UPDATE {base_table} base
        JOIN {competitor_table} competitor
        ON base.dialprefix = competitor.dialprefix 
      SET base.weight = CASE
        WHEN base.buyrate is not NULL and base.buyrate <= competitor.buyrate THEN {wight_good}
        ELSE {wight_bad}
        END
    """.format(
      base_table=base_table,
      competitor_table=competitor_table,
      wight_good=self.PRIMARY_ROUTE_WEIGHT,
      wight_bad=self.SECONDARY_ROUTE_WEIGHT
    )
    self._sql_helper.execute(query)

  def assign_route_weights(self, base_supplier, comparison_supplier):
    """
    Assign the route weight to the base_supplier merged table comparing the buyprice with the buyprice in the
    comparison_supplier merged table.
    :param base_supplier: name of the base supplier
    :param comparison_supplier: name of the comparison supplier
    """
    base_merged_tb = RATECARD_CONFIG[base_supplier]['merged_table'].format(
      origin_country_code=self._origin_country_code)
    comparison_merged_tb = RATECARD_CONFIG[comparison_supplier]['merged_table'].format(
      origin_country_code=self._origin_country_code)

    self._logger.info(
      "***** EVALUATING best ratecard route between {base_supplier} and {comparison_supplier} and ASSIGNING route weight to {base_supplier} - {country_name} *****".format(
        comparison_supplier=comparison_supplier,
        base_supplier=base_supplier,
        country_name=COUNTRY_CODE_NAME_MAP[self._origin_country_code]
      )
    )
    self._logger.log("PRIMARY ROUTE weight: {}; SECONDARY ROUTE weight: {}".format(self.PRIMARY_ROUTE_WEIGHT,
                                                                                   self.SECONDARY_ROUTE_WEIGHT))
    self._add_column_weight(base_merged_tb)
    self._assign_weights_by_buyrate(base_merged_tb, comparison_merged_tb)
    self._logger.success("Everything worked as expected. Double check to be sure.")

