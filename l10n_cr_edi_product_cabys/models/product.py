# Copyright 2020 Vauxoo
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).


from odoo import api, fields, models
from odoo.osv import expression


class L10nCrEdiProductCabys(models.Model):

    """Product and Service Codes from DGT Data.
    This code must be defined in all eInvoicing XML version 3.3, as
    of December 1, 2020.
    This is set by each product.
    Is defined a new catalog to only allow select the codes defined by the DGT
    that are load by data in the system.
    This catalog is found `here
    <https://activos.bccr.fi.cr/sitios/bccr/indicadoreseconomicos/cabys/Catalogo-de-bienes-servicios.xlsx>`_
    """
    _name = 'l10n.cr.edi.product.cabys'
    _description = "Product and Service Codes from DGT Data"

    code = fields.Char(
        help='This value is required in all eInvoicing XML version 4.3 to express the code of the '
        'product or service covered by the present concept. Must be used a key from the DGT catalog (CABYS).',
        required=True)
    name = fields.Char(
        help='Name defined by DGT CABYS for this product',
        required=True)
    tax_amount = fields.Char(help="Tax amount")
    active = fields.Boolean(
        help='If this record is not active, this cannot be selected.',
        default=True)

    def name_get(self):
        result = []
        for cabys in self:
            result.append((cabys.id, "%s %s" % (cabys.code, cabys.name or '')))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        if operator == 'ilike' and not (name or '').strip():
            domain = []
        else:
            domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    _sql_constraints = [
        ('code_cabys_uniq', 'unique(code)', 'The code must be unique per CABYS!'),
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_cr_edi_code_cabys_id = fields.Many2one(
        'l10n.cr.edi.product.cabys', 'CABYS code',
        help='This value is required in all eInvoicing XML version 4.3 to express the code of the '
        'product or service covered by the present concept. Must be used a key from the DGT catalog (CABYS).')
