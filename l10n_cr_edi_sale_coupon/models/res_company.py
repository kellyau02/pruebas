from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_cr_edi_not_delivery_discount = fields.Boolean(string='Not Apply Discount to Delivery Product')
