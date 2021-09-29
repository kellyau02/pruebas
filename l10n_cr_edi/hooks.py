# pylint: disable-all
# flake8: noqa

import logging
import psycopg2
from psycopg2 import sql

from odoo import api, SUPERUSER_ID
from odoo.tools import convert_file, mute_logger

_logger = logging.getLogger(__name__)


def pre_init_hook(cr):
    update_cabys_data(cr)
    update_data_economic_activity(cr)
    update_l10n_cr_uom_data(cr)
    update_toponomy_references(cr)
    remove_deprecated(cr)
    remove_uncertified_data(cr)


def post_init_hook(cr, registry):
    update_state_references(cr)


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
        query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE '{}'"
        cr.execute(sql.SQL(query.format(table)))
        columns = []
        for data in cr.fetchall():
            if data[0] != column:
                columns.append(data[0])

        if len(columns) <= 1:
            # unique key treated
            query = """
                UPDATE "{table}" as ___tu
                SET "{column}" = %s
                WHERE
                    "{column}" = %s AND
                    NOT EXISTS (
                        SELECT 1
                        FROM "{table}" as ___tw
                        WHERE
                            "{column}" = %s AND
                            ___tu.{value} = ___tw.{value}
                    )"""
            cr.execute(sql.SQL(query.format(table=table, column=column, value=columns[0])),
                       (dst_state.id, src_state.id, dst_state.id))
        else:
            try:
                with mute_logger('odoo.sql_db'), cr.savepoint():
                    query = 'UPDATE "{table}" SET "{column}" = %s WHERE "{column}" IN %s'
                    cr.execute(sql.SQL(query.format(table=table, column=column)), (dst_state.id, tuple(src_state.ids)))

            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent state_id is useless, better delete it
                query = 'DELETE FROM "{table}" WHERE "{column}" IN %s'
                cr.execute(sql.SQL(query.format(table=table, column=column)), tuple(src_state.ids))


def update_state_references(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})

        states = env['res.country.state'].search([
            ('country_id', '=', env.ref('base.cr').id),
        ])
        for state in states:
            state.write({'code': 'temp-%s' % state.code})

        convert_file(
            cr, 'l10n_cr_edi', 'data/res.country.state.csv',
            {}, 'init', True, 'data')
        new_states = env.ref('base.state_SJ')
        new_states |= env.ref('base.state_A')
        new_states |= env.ref('base.state_C')
        new_states |= env.ref('base.state_H')
        new_states |= env.ref('base.state_G')
        new_states |= env.ref('base.state_P')
        new_states |= env.ref('base.state_L')


        # Now update records with new state
        for state in states:
            dst_state = env['res.country.state'].search([
                ('country_id', '=', env.ref('base.cr').id),
                ('name', 'ilike', state.name),
                ('id', '!=', state.id),
            ], limit=1)
            if not dst_state:
                continue

            _update_foreign_keys(cr, state, dst_state)
            state.unlink()


def update_data_economic_activity(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi', model = 'l10n.cr.account.invoice.economic.activity'
            WHERE
                module = 'l10n_cr_einvoicing_base' and model = 'account.invoice.economic.activity'""")
        env.cr.execute("""
            ALTER TABLE IF EXISTS
                account_invoice_economic_activity
            RENAME TO
                l10n_cr_account_invoice_economic_activity""")
        env.cr.execute("""
            ALTER TABLE IF EXISTS
                account_invoice_economic_activity_res_company_rel
            RENAME TO
                l10n_cr_account_invoice_economic_activity_res_company_rel""")
        env.cr.execute("""
            ALTER TABLE IF EXISTS
                l10n_cr_account_invoice_economic_activity_res_company_rel
            RENAME account_invoice_economic_activity_id TO
                l10n_cr_account_invoice_economic_activity_id""")


def update_cabys_data(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi'
            WHERE
                module = 'l10n_cr_einvoicing_base' and name = 'l10n_cr_edi_date_for_cabys_change'""")


def update_l10n_cr_uom_data(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi'
            WHERE
                module = 'l10n_cr' and model = 'l10n_cr.uom'""")


def update_toponomy_references(cr):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi'
            WHERE
                module = 'l10n_cr_einvoicing_base' and model = 'res.country.state.canton'""")
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi'
            WHERE
                module = 'l10n_cr_einvoicing_base' and model = 'res.country.state.canton.district'""")
        env.cr.execute("""
            UPDATE
                ir_model_data
            SET
                module = 'l10n_cr_edi'
            WHERE
                module = 'l10n_cr_einvoicing_base' and model = 'res.country.state.canton.district.neighborhood'""")


MODELS_TO_DELETE = (
    'ir.actions.act_window',
    'ir.actions.act_window.view',
    'ir.actions.report.xml',
    'ir.actions.todo',
    'ir.actions.url',
    'ir.actions.wizard',
    'ir.cron',
    'ir.model',
    'ir.model.access',
    'ir.model.fields',
    'ir.module.repository',
    'ir.property',
    'ir.report.custom',
    'ir.report.custom.fields',
    'ir.rule',
    'ir.sequence',
    'ir.sequence.type',
    'ir.ui.menu',
    'ir.ui.view',
    'ir.ui.view_sc',
    'ir.values',
    'res.groups',
)


MODULES_TO_CLEAN = (
    'l10n_cr_einvoicing_cyberfuel',
    'l10n_cr_einvoicing_base',
    'l10n_cr_edi_addendas',
)


def model_to_table(model):
    """
    Get a table name according to a model name In case the table name is set on
    an specific model manually instead the replacement, then you need to add it
    in the mapped dictionary.
    """
    model_table_map = {
        'ir.actions.client': 'ir_act_client',
        'ir.actions.actions': 'ir_actions',
        'ir.actions.report.custom': 'ir_act_report_custom',
        'ir.actions.report.xml': 'ir_act_report_xml',
        'ir.actions.act_window': 'ir_act_window',
        'ir.actions.act_window.view': 'ir_act_window_view',
        'ir.actions.url': 'ir_act_url',
        'ir.actions.act_url': 'ir_act_url',
        'ir.actions.server': 'ir_act_server',
    }
    name = model_table_map.get(model)
    if name is not None:
        return name.replace('.', '_')
    if model is not None:
        return model.replace('.', '_')
    return ''


def table_exists(cr, table_name):
    cr.execute("SELECT count(1) FROM information_schema.tables WHERE "
               "table_name = %s and table_schema='public'",
               [table_name])
    return cr.fetchone()[0]


def remove_deprecated(cr):
    for m in MODULES_TO_CLEAN:
        cr.execute("UPDATE ir_module_module "
                   "set (state, latest_version) = ('uninstalled', False)"
                   " WHERE name = '{0}'".format(m))
        _logger.info('module to uninstall {0}'.format(m))


def module_delete(cr, module_name):
    _logger.info('deleting module {0}'.format(module_name))

    def table_exists(table_name):
        cr.execute("SELECT count(1) "
                   "FROM information_schema.tables "
                   "WHERE table_name = %s and table_schema='public'",
                   [table_name])
        return cr.fetchone()[0]
    cr.execute("SELECT res_id, model "
               "FROM ir_model_data "
               "WHERE module=%s and model in %s order by res_id desc",
               (module_name, MODELS_TO_DELETE))
    data_to_delete = cr.fetchall()
    for rec in data_to_delete:
        table = model_to_table(rec[1])
        cr.execute("SELECT count(*) "
                   "FROM ir_model_data "
                   "WHERE model = %s and res_id = %s", [rec[1], rec[0]])
        count1 = cr.dictfetchone()['count']
        if count1 > 1:
            continue
        try:
            # ir_ui_view
            if table == 'ir_ui_view':
                cr.execute('SELECT model '
                           'FROM ir_ui_view WHERE id = %s', (rec[0],))
                t_name = cr.fetchone()
                if not t_name:
                    continue
                table_name = model_to_table(t_name[0])
                cr.execute("SELECT viewname "
                           "FROM pg_catalog.pg_views "
                           "WHERE viewname = %s", [table_name])
                if cr.fetchall():
                    cr.execute('drop view ' + table_name + ' CASCADE')
                cr.execute('DELETE FROM ir_model_constraint '
                           'WHERE model=%s', (rec[0],))
                cr.execute('DELETE FROM ' + table + ' WHERE inherit_id=%s',
                           (rec[0],))
                cr.execute('SELECT * FROM ' + table + ' WHERE id=%s',
                           (rec[0],))
                view_exists = cr.fetchone()
                if bool(view_exists):
                    cr.execute('DELETE FROM ' + table + ' WHERE id=%s',
                               (rec[0],))

            # ir_act_window:
            elif table == 'ir_model':
                if table_exists('ir_model_constraint'):
                    cr.execute('DELETE FROM ir_model_constraint '
                               'WHERE model=%s', (rec[0],))
                if table_exists('ir_model_relation'):
                    cr.execute('DELETE FROM ir_model_relation '
                               'WHERE model=%s', (rec[0],))
                cr.execute('DELETE FROM ' + table + ' WHERE id=%s', (rec[0],))
            else:
                cr.execute('DELETE FROM ' + table + ' WHERE id=%s', (rec[0],))

            # also DELETE dependencies:
            cr.execute('DELETE FROM ir_module_module_dependency '
                       'WHERE module_id = %s', (rec[0],))
        except Exception as ex:
            msg = ("Module delete error\n"
                   "Model: {0}, id: {1}\n"
                   "Query: {2}\n"
                   "Error: {3}\n"
                   "On Module: {4}\n"
                   "").format(rec[1], rec[0],
                              cr.query, str(ex),
                              module_name)
            _logger.info(msg)
            # cr.execute("rollback to savepoint module_delete")
        else:
            _logger.info('Query on Else is %s' % cr.query)
            # cr.execute("release savepoint module_delete")

    cr.execute("DELETE FROM ir_model_data WHERE module=%s", (module_name,))
    cr.execute('UPDATE ir_module_module set state=%s WHERE name=%s',
               ('uninstalled', module_name))


def remove_uncertified_data(cr):
    for m in MODULES_TO_CLEAN:
        module_delete(cr, m)
