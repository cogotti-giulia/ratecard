RATECARD_CONFIG = {
  'twt': {
    'ratecard_table': 'twt_ratecard_{origin_country_code}',
    'surcharge_table': 'twt_surcharge_{origin_country_code}',
    'merged_table': 'twt_ratecard_merged_{origin_country_code}',
    'dialprefix_idx': 'twt_{origin_country_code}_dialprefix_IDX',
    # to standardize xlxs header column names
    'surcharge_columns': {
      'ORIGIN NAME': 'origin_name',
      'ORIGIN PREFIX': 'origin_prefix',
      'DESTINATION': 'destination',
      'SUR EUR': 'surcharge_eur',
    }
  },
  'colt': {
    'ratecard_table': 'colt_ratecard_{origin_country_code}',  # to be formatted with origin country
    'surcharge_table': 'colt_surcharge_{origin_country_code}',
    'merged_table': 'colt_ratecard_merged_{origin_country_code}',
    'dialprefix_idx': 'colt_{origin_country_code}_dialprefix_IDX',
    # to standardize xlxs header column names
    'surcharge_columns': {
      'Origin Country': 'origin_name',
      'Destination_x': 'destination',
      'Surcharge in EUR/minute': 'surcharge_eur',
    }
  }
}

BATCH_INSERT_SIZE = 5000