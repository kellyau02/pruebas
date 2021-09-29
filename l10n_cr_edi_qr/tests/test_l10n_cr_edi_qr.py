# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class InvoiceTransactionCase(AccountingTestCase):
    def setUp(self):
        super(InvoiceTransactionCase, self).setUp()
        self.invoice_model = self.env['account.move']
        self.account_settings = self.env['res.config.settings']

        self.company = self.env.user.company_id

    def test_l10n_cr_edi_generate_qr_code_url(self):
        invoice = self.invoice_model.create({})

        # Test invoice for Company out of CR
        self.company.country_id = self.env.ref('base.us')
        self.assertFalse(invoice.l10n_cr_edi_generate_qr_code_url())
        self.company.country_id = self.env.ref('base.cr')

        # Test invoice without l10n_cr_edi_full_number
        qr_expected = '/report/barcode/?type=QR&value=http%3A%2F%2Fwww.example.com&width=80&height=80&humanreadable=1'
        self.assertEqual(invoice.l10n_cr_edi_generate_qr_code_url(), qr_expected)

        # Test invoice with l10n_cr_edi_full_number
        invoice.l10n_cr_edi_full_number = '50631072000011363048500100001010000000015146241025'
        qr_expected = ('/report/barcode/?type=QR&value=https%3A%2F%2Fwww.comprobanteselectronicoscr.com'
                       '%2Fver.php%3Fclave%3D50631072000011363048500100001010000000015146241025&width=80&'
                       'height=80&humanreadable=1')
        self.assertEqual(invoice.l10n_cr_edi_generate_qr_code_url(), qr_expected)
