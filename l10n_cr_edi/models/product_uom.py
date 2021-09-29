# Copyright 2016 Vauxoo

from odoo import models, fields


class ProductUom(models.Model):
    _inherit = 'uom.uom'

    l10n_cr_edi_code = fields.Char(
        string='CR eInvoicing code',
        help='CR eInvoicing code')


class UnidOfMeasureForEinvoice(models.Model):
    _description = "Unit of measure for einvoice"
    _name = 'l10n_cr.uom'

    # TODO: improve help strings
    code = fields.Char(help='Code')
    name = fields.Char(help='Name')
    uom_type = fields.Selection(
        selection=[
            ('service', 'Service'),
            ('product', 'Product'),
            ('other', 'Other')
        ],
        help="Type")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_default_l10n_cr(self):
        result = self.env['l10n_cr.uom'].search(
            [('code', '=', 'Unid')], limit=1)
        return result.id

    l10n_cr_edi_uom_id = fields.Many2one(
        'l10n_cr.uom',
        string='Unit of measure for invoicing in CR.',
        help='Unit of measure for invoicing in CR.',
        default=_get_default_l10n_cr)

    l10n_cr_edi_tariff_heading = fields.Char(
        string='Tariff heading',
        help='Tariff heading')
