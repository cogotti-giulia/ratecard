import argparse
import sys

from utils.costants import ORIGIN_COUNTRY_CH, COUNTRY_PREFIX_MAP, COUNTRY_CODE_NAME_MAP
from utils.database.db_connect import get_db_connection
from utils.ratecard.twt import RateCardTwt
from utils.ratecard.colt import RateCardColt
from utils.style import Logger


def validate_arguments(args):

  supplier = args.supplier

  # TODO specifica meglio gli errori dai su che non e' detto che sarai tu a usarlo o ad essere qua

  if 'twt' in supplier:
    # check twt filenames
    if not args.ratecard_twt_fn or not args.surcharge_twt_fn:
      Logger.error("You must provide both ratecard and surcharge filenames (--ratecard-twt-fn and --surcharge-twt-fn) for twt.")
      return False

  if 'colt' in supplier:
    # check colt filenames
    if not args.ratecard_colt_fn or not args.surcharge_origin_colt_fn or not args.surcharge_asr_colt_fn:
      Logger.error("You must provide both ratecard and surcharges filenames (--ratecard-colt-fn and --surcharge-origin-colt-fn --surcharge-asr-colt-fn) for twt.")
      return False

  return True

# TODO accept arguments to decide
# origin_country
# supplier, twt, colt or both
# clean_existing to drop everything
# add a dry run mode
# and a show more debug print lines
def main(args):

  # HERE CHECK DATA PASSED
  is_everything_good = validate_arguments(args)
  if not is_everything_good:
    sys.exit(1)

  with get_db_connection() as conn:
    if conn and conn.is_connected():
      for origin_country_code in args.surcharge_origin:
      # origin_country =  args.surcharge_origin[0]
      #
          if 'twt' in args.supplier:
            twt = RateCardTwt(
              conn,
              origin_country_code=origin_country_code,
              ratecard_fn=args.ratecard_twt_fn,#'docs/twt/Rates_VOIPTEL INTERNATIONAL SA (SWD Voip)_SWITCHED GOLD - DIRETTO_20220527_125057.csv',
              surcharge_fn=args.surcharge_twt_fn#'docs/twt/OBR_TWT_20230804.xlsx'
            )
            twt.generate(
              # clean_existing=False
            )
            print '\n'

          if 'colt' in args.supplier:
            colt = RateCardColt(
              conn,
              origin_country_code=origin_country_code,
              ratecard_fn=args.ratecard_colt_fn,
              surcharge_origin_fn=args.surcharge_origin_colt_fn,#'docs/colt/Colt-Voice-Origin-Surcharges-v.87.0.xlsx',
              surcharge_asr_fn=args.surcharge_asr_colt_fn#'docs/colt/Origination-Charges-ASR-January-2024.XLS.xlsx'
            )
            colt.generate(
              # clean_existing=False
            )

          # TODO MERGE

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description=u"A script to handle ratecard import, apply of surcharge and merging of them.")
  # bohhh cosa devo passare?
  # origin_country sicuro -o --origin-country
  # TODO make them as choices ??? yup, like supported countries
  parser.add_argument(
    '-o', '--surcharge-origin',
    type=str,
    nargs="+",
    choices=COUNTRY_CODE_NAME_MAP.keys(),
    help=u"The origin country to apply surcharge for."
  )

  # se voglio importare i listini oppure no, tipo un -i per importare --should-import
  # TODO boh capire se droppare tutto e basta ogni volta oppure no

  # dovrei specificare i file per ognuno invece di hard codarli but colt ne ha due AAAAAAAAAAA
  # -s --supplier e accetta colt e twt
  parser.add_argument(
    '-s', '--supplier',
    nargs='+',
    choices=['colt', 'twt'],
    help=u"The suppliers to import ratecard, apply surcharge and merging (if more than one)."
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
  # se twt --ratecard-twt-fn e --surcharg-fn
  # se colt --ratecard --surcharge_origin_fn --surcharge_fn
  # -c --clean-existing to drop everything on the db ?? probably should allow the drop ratecard or surcharge ??? idkkkkkk
  # ma adesso metto il surcharge direttamente nel
  # --dry-run che non fa nulla nel db
  # --verbose per stampare tutto

  main(parser.parse_args())
