import time

import pandas as pd

from utils.ratecard.base import RateCardGenerationService
from utils.config import RATECARD_CONFIG, BATCH_INSERT_SIZE
from utils.costants import COUNTRY_PREFIX_MAP, COUNTRY_CODE_NAME_MAP

cfg = RATECARD_CONFIG['twt']


class RateCardTwt(RateCardGenerationService):
  STANDARDIZED_SURCHARGE_COLUMNS = {
    'ORIGIN NAME': 'origin_name',
    'ORIGIN PREFIX': 'origin_prefix',
    'DESTINATION': 'destination',
    'SUR EUR': 'surcharge_eur',
  }

  def __init__(self, conn, origin_country_code, ratecard_fn, surcharge_fn):
    self._surcharge_fn = surcharge_fn
    self.STANDARDIZED_SURCHARGE_COLUMNS = cfg['surcharge_columns']
    super(RateCardTwt, self).__init__(
      conn,
      COUNTRY_CODE_NAME_MAP[origin_country_code],
      ratecard_fn,
      ratecard_table=cfg['ratecard_table'].format(origin_country_code=origin_country_code),
      surcharge_table=cfg['surcharge_table'].format(origin_country_code=origin_country_code),
      dialprefix_idx=cfg['dialprefix_idx'].format(origin_country_code=origin_country_code),
    )
    self._logger.info("***** RATECARD TWT - {} *****".format(COUNTRY_CODE_NAME_MAP[origin_country_code]))

  def _load_surcharge_data(self, clean_existing=True):
    self._logger.info("Importing {} into table {}".format(self._surcharge_fn, self._surcharge_table))
    if clean_existing:
      self._drop_existing_tables(self._surcharge_table)
    self._create_surcharge_table()
    # Load all data
    df = pd.read_excel(self._surcharge_fn, header=2)
    # Identify the split point
    # look for the row where the first column repeats the header name
    first_col_header = df.columns[0]
    split_idx = df[df[first_col_header] == first_col_header].index

    if not split_idx.empty:
      idx = split_idx[0]
      # first table
      df1 = df.iloc[:idx].copy()
      # second table (skip the header row at idx)
      df2 = df.iloc[idx + 1:].copy()
      # This suppose that headers are the same otherwise it may be needed to reset columns if headers are actually different
      # df2.columns = df.iloc[idx]
      data_frames = [df1, df2]
    else:
      data_frames = [
        df]  # in case twt wakes up and decides to use one table as every human would have done on this planet

    # 2. Process and Insert
    with self._conn.cursor() as cursor:
      sql = "INSERT INTO {0} (origin_name, origin_prefix, destination, surcharge_eur) VALUES (%s, %s, %s, %s)".format(
        self._surcharge_table)

      for sub_df in data_frames:
        # Clean
        sub_df.dropna(how="all", inplace=True)
        sub_df = sub_df.rename(columns=self.STANDARDIZED_SURCHARGE_COLUMNS)

        # Select and clean strings
        relevant_cols = ['origin_name', 'origin_prefix', 'destination', 'surcharge_eur']
        final_df = sub_df[relevant_cols].copy()

        final_df['origin_name'] = final_df['origin_name'].str.strip()
        final_df['destination'] = final_df['destination'].str.strip()

        # Handle NaN -> None safely for SQL
        values_to_insert = final_df.where(pd.notnull(final_df), None).values.tolist()

        # Batch Insert
        for i in range(0, len(values_to_insert), BATCH_INSERT_SIZE):
          cursor.executemany(sql, values_to_insert)

        self._logger.log("Inserted batch of {} records.".format(len(values_to_insert)))

  def _apply_surcharge_to_ratecard(self):
    start = time.time()
    origin_country_prefix = COUNTRY_PREFIX_MAP[self._origin_country]
    self._logger.info(
      "Applying surcharge for all {} ({}) destinations...".format(self._origin_country, origin_country_prefix))
    with self._conn.cursor() as cursor:
      sql = """UPDATE {ratecard_table} rc
              JOIN {surcharge_table} ts1 on rc.destination = ts1.destination 
              SET rc.buyrate = (rc.buyrate + ts1.surcharge_eur)
              WHERE (ts1.origin_name = %(origin_name)s 
                OR ((ts1.origin_name = 'ROW' AND ts1.origin_prefix LIKE %(origin_prefix)s) 
                  AND NOT EXISTS (
                    SELECT 1
                    FROM {surcharge_table} sur_inner
                    WHERE sur_inner.destination = ts1.destination
                      AND sur_inner.origin_name = %(origin_name)s
                  )
                )
              );""".format(ratecard_table=self._ratecard_table, surcharge_table=self._surcharge_table)

      cursor.execute(sql, {'origin_name': self._origin_country, 'origin_prefix': str(origin_country_prefix)[0] + '%%'})
      end = time.time()
      self._logger.log(".....applied surcharge for {} destinations {:.4f}s".format(cursor.rowcount, end - start))
    # dovrei matchare le destination da listino a surcharge
    # per le origin swiss, italia, quello che voglio
    # se ho italy e match di destination ok applico
    # --- righe ROW ---
    # ORIGIN Switzerland che ha prefix 41
    # DESTINATION Italy Mobile Vodafone non ha una riga nel surcharge di Switzerland 41
    # ma esiste la ROW 4 con quella destination, quindi ricade la
