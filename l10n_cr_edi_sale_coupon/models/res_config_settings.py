from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_cr_edi_not_delivery_discount = fields.Boolean(
        string='Not Apply Discount to Delivery Product',
        readonly=False,
        related='company_id.l10n_cr_edi_not_delivery_discount')
