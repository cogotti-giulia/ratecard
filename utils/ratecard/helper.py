from utils.config import RATECARD_CONFIG
from utils.database.sql import SqlHelper
from utils.exporter import BaseSqlExporter
from utils.style import Logger


class RateCardHelper(object):

  def __init__(self, conn, origin_country_code):
    self._conn = conn
    self._origin_country_code = origin_country_code
    self._sql_helper = SqlHelper(conn)
    self._logger = Logger()

  def export_satellite_ratecard(self, supplier_one, supplier_two, percentage_increase=40):
    """
    Exports a xls file for satellite ratecard

    Satellite means all dialprefix that starts with 870, 881, 882

    :param supplier_one: name of supplier one to get merged ratecard from
    :param supplier_two: name of suppliers two to get merged ratecard from
    :param percentage_increase: increase to add in percentage to the buyprice
    """
    self.export_by_root_prefix(supplier_one, supplier_two, percentage_increase, base_prefix_lst=[870, 881, 882], base_filename="satellite_")

  def export_by_root_prefix(self, supplier_one, supplier_two, percentage_increase, base_prefix_lst=None, logic="OR", base_filename=''):
    """
    Exports a xls file for ratecard starting with dialprefix in base_prefix_lst, choosing by the route weight between
    the supplier one and the supplier two

    File columns:
      dialprefix
      destination
      buyprice (increased in percentage using the percentage_increase parameter)
      supplier (the name of the supplier with the lower buyprice)

    :param supplier_one: name of supplier one to get merged ratecard from
    :param supplier_two: name of suppliers two to get merged ratecard from
    :param percentage_increase: to add in percentage to the buyprice
    :param base_prefix_lst: list of dialprefix
    :param logic: "AND" or "OR" to compose condition in base_prefix_lst
    :param base_filename: suffix to prepend to base filename
    """
    sup1_table = RATECARD_CONFIG[supplier_one]['merged_table'].format(
      origin_country_code=self._origin_country_code)
    sup2_table = RATECARD_CONFIG[supplier_two]['merged_table'].format(
      origin_country_code=self._origin_country_code)

    def build_like_condition(supplier):
      return (' ' + logic + ' ').join(
        [supplier_one + ".dialprefix LIKE '" + str(base_prefix) + "%'" for base_prefix in base_prefix_lst])

    s1_conditions = build_like_condition(supplier_one)
    s2_conditions = build_like_condition(supplier_two)
    full_condition = ("(" + s1_conditions + ")" + ' AND ' + "(" + s2_conditions + ")")

    sql = """
    SELECT {one}.dialprefix, 
      CASE WHEN {one}.weight < {two}.weight 
        THEN {one}.destination 
        ELSE {two}.destination 
      END AS destination,
      CASE WHEN {one}.weight < {two}.weight 
        THEN {one}.buyrate + ({one}.buyrate * {percentage_increase} / 100) 
        ELSE {two}.buyrate + ({two}.buyrate * 40 / 100) 
      END AS buyrate,
      CASE WHEN {one}.weight < {two}.weight 
        THEN "{one}" 
        ELSE "{two}" 
      END AS supplier
    FROM {supplier_one_table} {one} JOIN {supplier_two_table} {two} ON {one}.dialprefix = {two}.dialprefix 
    WHERE {conditions};
    """.format(
      supplier_one_table=sup1_table,
      supplier_two_table=sup2_table,
      one=supplier_one,
      two=supplier_two,
      percentage_increase=percentage_increase,
      conditions=full_condition
    )
    filename = base_filename if base_filename else "_".join(base_prefix_lst)
    filename += 'ratecard_{}'.format(self._origin_country_code)
    exporter = BaseSqlExporter(self._conn, filename=filename)

    print (exporter.to_excel(sql))
