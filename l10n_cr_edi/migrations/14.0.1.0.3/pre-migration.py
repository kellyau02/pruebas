import psycopg2
from odoo import SUPERUSER_ID, api
from odoo.tools import mute_logger


def _get_fk_on(cr, table):
    """ return a list of many2one relation with the given table.
        :param table : the name of the sql table to return relations
        :returns a list of tuple 'table name', 'column name'.
    """
    query = """
        SELECT cl1.relname as table, att1.attname as column
        FROM pg_constraint as con, pg_class as cl1, pg_class as cl2, pg_attribute as att1, pg_attribute as att2
        WHERE con.conrelid = cl1.oid
            AND con.confrelid = cl2.oid
            AND array_lower(con.conkey, 1) = 1
            AND con.conkey[1] = att1.attnum
            AND att1.attrelid = cl1.oid
            AND cl2.relname = %s
            AND att2.attname = 'id'
            AND array_lower(con.confkey, 1) = 1
            AND con.confkey[1] = att2.attnum
            AND att2.attrelid = cl2.oid
            AND con.contype = 'f'
    """
    cr.execute(query, (table,))
    return cr.fetchall()


def _update_foreign_keys(cr, src_state, dst_state):
    """ Update all foreign key from the src_state to dst_state. All many2one fields will be updated.
        :param src_state : source res.country.state recordset
        :param dst_state : record of destination res.country.state
    """
    relations = _get_fk_on(cr, 'res_country_state')

    for table, column in relations:
        query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE '%s'" % (table)
        cr.execute(query, ())
        columns = []
        for data in cr.fetchall():
            if data[0] != column:
                columns.append(data[0])

        # do the update for the current table/column in SQL
        query_dic = {
            'table': table,
            'column': column,
            'value': columns[0],
        }
        if len(columns) <= 1:
            # unique key treated
            query = """
                UPDATE "%(table)s" as ___tu
                SET "%(column)s" = %%s
                WHERE
                    "%(column)s" = %%s AND
                    NOT EXISTS (
                        SELECT 1
                        FROM "%(table)s" as ___tw
                        WHERE
                            "%(column)s" = %%s AND
                            ___tu.%(value)s = ___tw.%(value)s
                    )""" % query_dic
            cr.execute(query, (dst_state.id, src_state.id, dst_state.id))
        else:
            try:
                with mute_logger('odoo.sql_db'), cr.savepoint():
                    query = 'UPDATE "%(table)s" SET "%(column)s" = %%s WHERE "%(column)s" IN %%s' % query_dic
                    cr.execute(query, (dst_state.id, tuple(src_state.ids),))

            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent state_id is useless, better delete it
                query = 'DELETE FROM "%(table)s" WHERE "%(column)s" IN %%s' % query_dic
                cr.execute(query, (tuple(src_state.ids),))


def update_res_country_state(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    states = {
        'state_1': 'state_SJ',
        'state_2': 'state_A',
        'state_3': 'state_C',
        'state_4': 'state_H',
        'state_5': 'state_G',
        'state_6': 'state_P',
        'state_7': 'state_L'
    }
    for src, dst in states.items():
        src_state = env.ref('l10n_cr_edi.%s' % src)
        dst_state = env.ref('base.%s' % dst)
        _update_foreign_keys(cr, src_state, dst_state)
        src_state.unlink()


def migrate(cr, version):
    if not version:
        return
    update_res_country_state(cr)
