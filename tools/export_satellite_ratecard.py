import argparse
import sys
from itertools import permutations

from utils.config import RATECARD_CONFIG
from utils.costants import COUNTRY_CODE_NAME_MAP
from utils.database.db_connect import get_db_connection
from utils.ratecard.helper import RateCardHelper
from utils.style import Logger


def validate_arguments(args):
  """
  Validates the arguments provided, basically checks if at least two suppliers are provided.
  :param args: parsed arguments
  :return: False if arguments are invalid, True otherwise
  """
  if len(args.suppliers) < 2:
    Logger.error("At least two suppliers must be specified.")
    return False
  return True


def main(args):
  is_everything_good = validate_arguments(args)
  if not is_everything_good:
    sys.exit(1)

  with get_db_connection() as conn:
    if conn and conn.is_connected():
      for origin_country_code in args.origin_country_codes:
        if len(args.suppliers) >= 2:
          rt_helper = RateCardHelper(conn, origin_country_code)

          for base, other in permutations(args.suppliers, 2):
            print base, other
            rt_helper.export_satellite_ratecard(base, other)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description="Simply perform some querying on the merged ratecards"
  )

  parser.add_argument(
    '-o', '--origin-country-codes',
    type=str,
    nargs="+",
    choices=COUNTRY_CODE_NAME_MAP.keys(),
    help=u"The origin country to apply surcharge for."
  )
  parser.add_argument(
    '-s', '--suppliers',
    nargs='+',
    choices=RATECARD_CONFIG.keys(),
    help=u"Supplier names to be considered"
  )

  main(parser.parse_args())
