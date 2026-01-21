import argparse
import sys
import time
from itertools import permutations

from utils.config import RATECARD_CONFIG, DEBUG_MODE
from utils.costants import COUNTRY_CODE_NAME_MAP
from utils.database.db_connect import get_db_connection
from utils.database.sql import SqlHelper
from utils.exporter import BaseSqlExporter
from utils.ratecard.evaluator import RatecardRouteEvaluator
from utils.ratecard.merger import SupplierRateCardMerger
from utils.ratecard.twt import RateCardTwt
from utils.ratecard.colt import RateCardColt
from utils.style import Logger


def validate_arguments(args):
  """
  Validates the arguments provided, basically for each supplier checks if the right files are provided.

  :param args: parsed arguments
  :return: False if arguments are invalid, True otherwise
  """
  supplier = args.suppliers

  if len(args.suppliers) < 2:
    Logger.error("At least two suppliers must be specified.")
    return False

  if 'twt' in supplier:
    # check twt filenames
    if not args.ratecard_twt_fn or not args.surcharge_twt_fn:
      Logger.error(
        "You must provide both ratecard and surcharge filenames (--ratecard-twt-fn and --surcharge-twt-fn) for twt.")
      return False

  if 'colt' in supplier:
    # check colt filenames
    if not args.ratecard_colt_fn or not args.surcharge_origin_colt_fn or not args.surcharge_asr_colt_fn:
      Logger.error(
        "You must provide both ratecard and surcharges filenames (--ratecard-colt-fn and --surcharge-origin-colt-fn --surcharge-asr-colt-fn) for twt.")
      return False

  return True


def main(args):
  is_everything_good = validate_arguments(args)
  start = time.time()
  if not is_everything_good:
    sys.exit(1)

  with get_db_connection() as conn:
    if conn and conn.is_connected():
      for origin_country_code in args.surcharge_origin:
        # generating ratecard and applying sourcharge for suppliers
        if 'twt' in args.suppliers:
          twt = RateCardTwt(
            conn,
            origin_country_code=origin_country_code,
            ratecard_fn=args.ratecard_twt_fn,
            surcharge_fn=args.surcharge_twt_fn
          )
          twt.generate(
            # clean_existing=False
          )
          print '\n'

        if 'colt' in args.suppliers:
          colt = RateCardColt(
            conn,
            origin_country_code=origin_country_code,
            ratecard_fn=args.ratecard_colt_fn,
            surcharge_origin_fn=args.surcharge_origin_colt_fn,
            surcharge_asr_fn=args.surcharge_asr_colt_fn
          )
          colt.generate(
            # clean_existing=False
          )

        # this works even if there are more than 2 suppliers
        if len(args.suppliers) > 1:
          combinator = SupplierRateCardMerger(conn, origin_country_code)
          evaluator = RatecardRouteEvaluator(conn, origin_country_code)

          for base, other in permutations(args.suppliers, 2):
            combinator.merge_into_base(base, other)
            evaluator.assign_route_weights(base, other)
          print '\n'

        if not DEBUG_MODE:
          sql_helper = SqlHelper(conn)
          ratecard_tables = [RATECARD_CONFIG[supplier]["ratecard_table"].format(origin_country_code=origin_country_code) for supplier in args.suppliers]
          surcharge_tables = [RATECARD_CONFIG[supplier]["surcharge_table"].format(origin_country_code=origin_country_code) for supplier in args.suppliers]
          tables = ratecard_tables + surcharge_tables
          sql_helper.drop_tables(tables)

        tables_to_export =  [RATECARD_CONFIG[supplier]["merged_table"].format(origin_country_code=origin_country_code) for supplier in args.suppliers]
        print(tables_to_export)
        for table in tables_to_export:
          query = """
          SELECT * FROM {table}
          WHERE buyrate IS NOT NULL;
          """.format(table=table)
          exporter = BaseSqlExporter(conn, table)
          exporter.to_csv(query)


  print '\n'
  end = time.time()
  Logger.success("Everything went great! At least i hope so. Execution time: {}".format(end-start))


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description=u"A script to handle ratecard import, apply of surcharge, merging and evaluation best route of them.")

  parser.add_argument(
    '-o', '--surcharge-origin',
    type=str,
    nargs="+",
    choices=COUNTRY_CODE_NAME_MAP.keys(),
    help=u"The origin country to apply surcharge for."
  )
  parser.add_argument(
    '-s', '--suppliers',
    nargs='+',
    choices=RATECARD_CONFIG.keys(),
    help=u"Supplier names to be considered for ratecard import, surcharge application, and mutual ratecard merging."
        "For every ordered supplier pair (A -> B and B -> A), merge and route-weight assignment operations are executed. "
        "At least two suppliers must be specified."
  )
  parser.add_argument(
    '--ratecard-twt-fn',
    type=str,
    help=u"The ratecard TWT file to import."
  )
  parser.add_argument(
    '--ratecard-colt-fn',
    type=str,
    help=u"The ratecard COLT file to import."
  )
  parser.add_argument(
    '--surcharge-twt-fn',
    type=str,
    help=u"The surcharge TWT file to import and apply on TWT ratecard."
  )
  parser.add_argument(
    '--surcharge-origin-colt-fn',
    type=str,
    help=u"The surcharge COLT file (the one specifying surcharge group for origin to destination) to combine with `surcharge-asr-fn` to apply on COLT ratecard."
  )
  parser.add_argument(
    '--surcharge-asr-colt-fn',
    type=str,
    help=u"The surcharge COLT file (the one with actual prices for the destination, based on surcharge group) to combine with `surcharge-origin-colt-fn` to apply on COLT ratecard."
  )
  # TODO
  # --dry-run
  # --verbose per stampare esageratamente
  # forse qualcosa per decidere se fare tutto da zero, o fare a pezzi, ma boh non mi pare fondamentale (non ho voglia ora sorry)

  main(parser.parse_args())
