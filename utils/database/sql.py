from utils.style import Logger


class SqlHelper:
  def __init__(self, conn):
    self._conn = conn
    self._logger = Logger()

  def create_table(self, table_name, columns):
    """
    Creates the table with the given name and columns.
    Raises an exception if something goes wrong in the db operation and rollback.

    :param table_name: Name of the table
    :param columns: A list of column tuples in the format (column_name, column_type, options).
      Example:
        [("dialprefix", "bigint", "DEFAULT NULL"),
        ("destination", "text"),
        ("buyrate", "double", "DEFAULT NULL")]
    :return:
    """
    try:
      with self._conn.cursor() as cursor:

        columns_sql = ",\n  ".join(
          "`{}` {} {}".format(name, col_type, opts).strip()
          for name, col_type, opts in columns
        )
        sql = """
         CREATE TABLE IF NOT EXISTS `{table}` (
          {columns}
        ) ENGINE=MyISAM DEFAULT CHARSET=latin1;
        """.format(table=table_name, columns=columns_sql)
        self._logger.log("Executing\n{}".format(sql))
        cursor.execute(sql)
        self._logger.log(".....yey")
      self._conn.commit()

    except Exception as e:
      self._conn.rollback()
      self._logger.error("Error during cancellation. Rolled back changes.", error_detail=e)
      raise

  def drop_tables(self, tables):
    """
    Drops the tables from the given list of tables, if they exist.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param tables: list of table names, or just a single str table name
    """
    try:
      with self._conn.cursor() as cursor:
        if isinstance(tables, str):
          tables = [tables]

        for table_name in tables:
          sql = """DROP TABLE IF EXISTS {0};""".format(table_name)
          self._logger.log("Executing\n{}".format(sql))
          cursor.execute(sql)
          self._logger.log(".....yey")

      self._conn.commit()
    except Exception as e:
      self._conn.rollback()
      self._logger.error("Error during cancellation. Rolled back changes.", error_detail=e)
      raise

  def create_index(self, idx, table, column):
    """
    Creates an index, doesn't check if it exists at the moment.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param idx: index name
    :param table: table name
    :param column: column name to apply the index to
    """
    try:
      with self._conn.cursor() as cursor:
        sql = """CREATE INDEX `{idx}` ON {table} ({column})""".format(
          idx=idx, table=table, column=column)
        self._logger.log("Executing\n{}".format(sql))
        cursor.execute(sql)
        self._logger.log(".....yey")

    except Exception as e:
      self._conn.rollback()
      self._logger.error("Error during cancellation. Rolled back changes.", error_detail=e)
      raise
