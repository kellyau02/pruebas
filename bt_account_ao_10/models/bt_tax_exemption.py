from odoo import fields, models, api


class bt_tax_exemption(models.Model):
    _inherit = 'l10n_cr_edi.tax.exemption'

    date_finish = fields.Date(string='Finish date')
