from odoo import models, fields


class PosOrder(models.Model):

    _inherit = 'pos.order'

    l10n_cr_edi_invoice_number = fields.Char(related='invoice_id.number')
    l10n_cr_edi_invoice_full_number = fields.Char(
        related='invoice_id.cr_einvoicing_full_number')
