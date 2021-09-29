# Copyright 2020 Vauxoo
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from os.path import join, dirname, realpath


def post_init_hook(cr, registry):
    _load_product_cabys(cr, registry)


def _load_product_cabys(cr, registry):
    """Import CSV data as it is faster than xml and because we can't use
    noupdate anymore with csv"""
    csv_path = join(dirname(realpath(__file__)), 'data',
                    'l10n.cr.edi.product.cabys.csv')
    csv_file = open(csv_path, 'rb')
    cr.copy_expert(
        """COPY l10n_cr_edi_product_cabys(code, name, tax_amount, active)
           FROM STDIN WITH DELIMITER '|'""", csv_file)
    # Create xml_id, to allow make reference to this data
    cr.execute(
        """INSERT INTO ir_model_data
           (name, res_id, module, model, noupdate)
           SELECT concat('prod_cabys_', code), id, 'l10n_cr_edi_product_cabys', 'l10n.cr.edi.product.cabys', 't'
           FROM l10n_cr_edi_product_cabys """)


def uninstall_hook(cr, registry):
    cr.execute("DELETE FROM l10n_cr_edi_product_cabys;")
    cr.execute(
        "DELETE FROM ir_model_data WHERE module='l10n_cr_edi_product_cabys';")
