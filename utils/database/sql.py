from utils.database.db_connect import get_connection_cursor
from utils.style import Logger


class SqlHelper:
  """Just a SQL helper class to perform simple operations"""

  def __init__(self, conn, engine="MyISAM"):
    self._conn = conn
    self._engine = engine
    self._logger = Logger()

  def execute(self, query, commit=False, func=None):
    """
    Execute a query and return the result
    :param query: sql query
    :param commit: whether to commit or not the result
    :param func: function to execute on the result
    """
    try:
      with get_connection_cursor(self._conn, commit) as cursor:
        self._logger.log("Executing\n{}".format(query))
        cursor.execute(query)
        self._logger.log(".....yey")
        if func:
          func(cursor)
        return cursor.fetchall()
    except Exception as e:
      self._conn.rollback()
      self._logger.error("Error executing query. Rolled back changes.", error_detail=e)
      raise

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

    columns_sql = ",\n  ".join(
      "`{}` {} {}".format(name, col_type, opts).strip()
      for name, col_type, opts in columns
    )
    sql = """
     CREATE TABLE IF NOT EXISTS `{table}` (
      {columns}
    ) ENGINE={engine} DEFAULT CHARSET=latin1;
    """.format(table=table_name, engine=self._engine, columns=columns_sql)

    self.execute(sql)

  def drop_tables(self, tables):
    """
    Drops the tables from the given list of tables, if they exist.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param tables: list of table names, or just a single str table name
    """
    if isinstance(tables, str):
      tables = [tables]
    for table_name in tables:
      sql = """
      DROP TABLE IF EXISTS {0};
      """.format(table_name)
      self.execute(sql)

  def create_index(self, idx, table, column):
    """
    Creates an index, doesn't check if it exists at the moment.
    Raises an exception if something goes wrong in the db operation and rollback.
    :param idx: index name
    :param table: table name
    :param column: column name to apply the index to
    """
    sql = """
           CREATE INDEX `{idx}` ON {table} ({column})
           """.format(idx=idx, table=table, column=column)
    self.execute(sql)
