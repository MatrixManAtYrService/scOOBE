import _mysql
from textwrap import dedent
from scoobe.common import StatusPrinter, Indent
from scoobe.ssh_common import SshConfig, SshTunnel

# encapsulates a mysql query
class Query:
    def __init__(self, ssh_config, mysql_user, mysql_pass, sql):
        self.ssh_config = ssh_config
        self.mysql_user = mysql_user
        self.mysql_pass = mysql_pass
        self.sql = sql
        self._empty_message = "Expected a nonempty result for Query: " + sql

    def on_empty(self, message):
        self._empty_message = message

    # called externally when the user doesn't need to read data
    # called internally, parameter will be called with post-query connection string
    def execute(self, then=lambda db : None, printer=StatusPrinter()):
        # open an ssh tunnel
        with SshTunnel(self.ssh_config, printer) as tun:
            with Indent(printer):
                # open a mysql connection
                db = _mysql.connect(user=self.mysql_user,
                                    host='127.0.0.1',
                                    port=tun.mysql_port,
                                    db='meta',
                                    passwd=self.mysql_pass)

                # show the query then run it
                printer("[Query]")
                with Indent(printer):
                    printer(dedent(self.sql).strip())
                db.query(self.sql)

                # do what the caller wanted
                return then(db)

    def get_from_first_row(self, getter, printer=StatusPrinter()):
        def get_row_val(db):
            row = db.store_result().fetch_row(how=1)
            if not row:
                printer("...got empty result")
                raise ValueError(self._empty_message)
            else:
                printer("[Result]")
                with Indent(printer):
                    try:
                        # if we're selecting rows directly
                        if isinstance(row, tuple):
                            printer(row[0])
                            return getter(row[0])
                        # if we're selecting the output of a mysql builtin
                        else:
                            printer(row)
                            return getter(row)
                    except:
                        printer(row[0])
                        raise

        row = self.execute(then=get_row_val, printer=printer)
        return row

