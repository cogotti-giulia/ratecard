import pandas as pd

from tabulate import tabulate

from utils.costants import COUNTRY_CODE_NAME_MAP
from utils.ratecard.base import RateCardGenerator
from utils.config import RATECARD_CONFIG

cfg = RATECARD_CONFIG['colt']

class RateCardColt(RateCardGenerator):

  def __init__(self, conn, origin_country_code, ratecard_fn, surcharge_origin_fn, surcharge_asr_fn):
    self._surcharge_origin_fn = surcharge_origin_fn
    self._surcharge_asr_fn = surcharge_asr_fn
    self.STANDARDIZED_SURCHARGE_COLUMNS = cfg['surcharge_columns']

    super(RateCardColt, self).__init__(
      conn,
      COUNTRY_CODE_NAME_MAP[origin_country_code],
      ratecard_fn,
      cfg['ratecard_table'].format(origin_country_short=origin_country_code),
      cfg['surcharge_table'].format(origin_country_short=origin_country_code)
    )
    self._logger.info("***** RATECARD COLT - {} *****".format(COUNTRY_CODE_NAME_MAP[origin_country_code]))

  def _import_surcharge(self, clean_existing=True):
    if clean_existing:
      self._clean_db(self._surcharge_table)
    self._create_surcharge_table()

    self._logger.info("Merging {} and {}".format(self._surcharge_origin_fn, self._surcharge_asr_fn))
    self._logger.info("Importing merged files into table {}".format(self._surcharge_table))

    df_one = pd.read_excel(self._surcharge_origin_fn, header=1)  # starts from 0
    header_one = list(df_one.columns)
    df_two = pd.read_excel(self._surcharge_asr_fn, header=11)  # starts from 0
    header_two = list(df_two.columns)

    # cleaning up data
    # usa loc quando hai condizioni per aggiornare
    df_two.loc[df_two['Surcharge in EUR/minute'] == '-', 'Surcharge in EUR/minute'] = 0
    # df_two['Surcharge in EUR/minute'] = df_two['Surcharge in EUR/minute'].replace('-', 0).astype('float')
    df_one['Destination Tier-Code'] = df_one['Destination Tier-Code'].str.strip().str.rstrip('-')
    df_one['Origin Surcharge Group'] = df_one['Origin Surcharge Group'].str.strip()
    df_one['temp_key'] = df_one['Destination Tier-Code'].astype(str) + '-' + df_one['Origin Surcharge Group'].astype(str)
    merged_df = pd.merge(
      df_one,
      df_two,
      left_on=['temp_key'],
      right_on=['Origin & Destination Rating Tier-Code'],
      how='left'
    )

    # 4. (Optional) Clean up
    # You can drop the temporary key and the redundant right key if you wish
    merged_df = merged_df.drop(columns=['temp_key'])

    # TODO converti anche qua nan in None e il trattino in 0, anzi il trattino in zero prima!!!
    # posso fare gia qua il warning dato che so la mia origin country ???? filtro il merged_df per origin
    # e vedo dove destination_y is null e printo la riga
    renamed_merged_df = merged_df.rename(columns=self.STANDARDIZED_SURCHARGE_COLUMNS)

    renamed_merged_df[['origin_name', 'destination', 'Origin Surcharge Group', 'Destination_y',
               'Origin & Destination Rating Tier-Code', 'surcharge_eur']].to_excel('docs/colt/merged_cut.xls',
                                                                                             index=False)

    df_to_log = renamed_merged_df.loc[
      (renamed_merged_df['origin_name'] == self._origin_country) &
      (renamed_merged_df['Origin & Destination Rating Tier-Code'].isnull())
      ][['origin_name', 'destination', 'Origin Surcharge Group']]

    self._logger.warning(
      "Some rows from '{0}' have missing rating tiers in '{1}'.\nThese destinations may not have been properly surcharged. Check the details below.".format(
        self._surcharge_origin_fn, self._surcharge_asr_fn
      ), warning_detail='\n'+tabulate(df_to_log, headers='keys', tablefmt='grid', showindex=False))


    # renamed_merged_df = renamed_merged_df.replace(np.nan, None)
    relevant_column_names = ['origin_name', 'destination', 'surcharge_eur']

    with self._conn.cursor() as cursor:
      sql = "INSERT INTO {0} (origin_name, destination, surcharge_eur) VALUES (%s, %s, %s)".format(
        self._surcharge_table)
      rows = (
        renamed_merged_df[relevant_column_names]
        .where(pd.notna(renamed_merged_df[relevant_column_names]), None)
        .values
        .tolist()
      )

      # for i in range(0, len(rows), BATCH_INSERT_SIZE):
      cursor.executemany(sql, rows)
      # cursor.executemany(sql, renamed_merged_df[relevant_column_names].values.tolist())
      self._logger.log("Successfully inserted {0} records.".format(renamed_merged_df.shape[0]))


  def _apply_surcharge(self):
    # easy ho gia le righe con origine e destinazione
    self._logger.info(
      "Applying surcharge for all {} destinations...".format(self._origin_country))
    with self._conn.cursor() as cursor:
      sql = """
        UPDATE {0} cl1
        JOIN {1} cs1 on cs1.destination = cl1.destination 
        SET cl1.buyrate = (cl1.buyrate + cs1.surcharge_eur)
        WHERE cs1.origin_name = %(origin_name)s AND cs1.surcharge_eur is not NULL;
      """.format(self._ratecard_table, self._surcharge_table)

      cursor.execute(sql, {'origin_name': self._origin_country})
      self._logger.log(".....applied surcharge for {} destinations".format(cursor.rowcount))
