from odoo import fields, models


class IrView(models.Model):
    _inherit = 'ir.ui.view'

    l10n_cr_edi_addenda_flag = fields.Boolean(
        string='Is an addenda?',
        help='If True, the view is an addenda for the Costarican EDI invoicing.',
        default=False)
