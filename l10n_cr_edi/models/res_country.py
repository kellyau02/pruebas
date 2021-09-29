from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = 'res.country.state'

    l10n_cr_edi_code = fields.Char(
        'Code CR', help='State code defined by the SAT in the catalog to '
        'EDI documents. Will be used in the XML files to indicate the state reference.')
