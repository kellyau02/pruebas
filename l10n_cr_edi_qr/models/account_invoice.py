# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

import werkzeug.urls
from odoo import api, models


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    @api.model
    def l10n_cr_edi_generate_qr_code_url(self):
        if not self.l10n_cr_edi_is_required():
            return False

        url = self.company_id.website
        if self.l10n_cr_edi_full_number:
            url = "https://www.comprobanteselectronicoscr.com/ver.php?clave="

        qr_code_string = '%s%s' % (url, self.l10n_cr_edi_full_number or '')
        qr_code_url = '/report/barcode/?type=%s&value=%s&width=%s&height=%s&humanreadable=1' % (
            'QR', werkzeug.url_quote_plus(qr_code_string), 80, 80)
        return qr_code_url
