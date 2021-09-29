from .common import TestCREdiCommon

from freezegun import freeze_time

from odoo.exceptions import ValidationError, UserError
from odoo.tests import Form, tagged


@tagged('edi_cr', 'post_install', '-at_install')
class TestL10nCrEdiInvoice(TestCREdiCommon):
    def test_01_l10n_cr_edi_invoice_basic(self):
        invoice = self.invoice

        # Ensure show correct economy activities
        activities = self.env['l10n.cr.account.invoice.economic.activity']
        self.assertEqual(invoice.company_id.l10n_cr_edi_economic_activity_ids, activities.search(
            invoice.with_context(default_move_type='out_invoice').domain_economic_activity()),
            'Error in domain for economy activities')
        self.assertEqual(activities.search([]), activities.search(
            invoice.with_context(default_move_type='in_invoice').domain_economic_activity()),
            'Error in domain for economy activities')

        # Test is electronic invoice
        journal_no_electronic = self.company_data['default_journal_bank'].copy()
        journal_no_electronic.sudo().l10n_cr_edi_document_type = False
        invoice_no_electronic = invoice.copy()
        invoice_no_electronic.journal_id = journal_no_electronic
        self.assertTrue(invoice.l10n_cr_edi_bool)
        self.assertFalse(invoice_no_electronic.l10n_cr_edi_bool)

        # Test _l10n_cr_edi_generate_document_name when theres is no type of document
        self.assertFalse(invoice_no_electronic._l10n_cr_edi_generate_document_name())

        # Test no comercial_partner_id
        no_commercial_partner = self.partner_a.copy()
        no_commercial_partner.sudo().commercial_partner_id = None
        invoice.partner_id = no_commercial_partner
        self.assertEqual(invoice._get_partner_to_email(), invoice.partner_id)

        # Test Economic Activity
        default_activity = invoice._get_default_l10n_cr_edi_economic_activity()
        self.assertEqual(default_activity, self.invoice.company_id.l10n_cr_edi_economic_activity_ids[0].id)

        # Test onchange reference type
        # When Reference type is not set
        with Form(invoice) as form:
            form.invoice_date = '2000-01-01'
            form.l10n_cr_edi_ref_num = '0000000'
            form.l10n_cr_edi_ref_doc = '01'
            form.l10n_cr_edi_ref_id = self.invoice_model.browse(1)
            form.l10n_cr_edi_ref_type = False
        self.assertFalse(any([
            invoice.l10n_cr_edi_ref_doc,
            invoice.l10n_cr_edi_ref_num,
            invoice.l10n_cr_edi_ref_id,
            invoice.invoice_date]))

        # FIXME psycopg2.IntegrityError: insert or update on table "account_move" violates foreign key constraint
        # "account_move_l10n_cr_edi_ref_id_fkey" the following code is pending to fix

        # When Reference type is 05
        # with Form(invoice) as form:
        #     form.invoice_date = '2000-01-01'
        #     form.l10n_cr_edi_ref_num = '0000000'
        #     form.l10n_cr_edi_ref_id = self.invoice_model.browse(1)
        #     form.l10n_cr_edi_ref_type = '05'
        #     form.l10n_cr_edi_ref_doc = '01'
        # self.assertTrue(all([
        #     invoice.l10n_cr_edi_ref_num,
        #     invoice.l10n_cr_edi_ref_id,
        #     invoice.invoice_date,
        # ]))

    def test_02_cyberfuel_doc_type(self):
        invoice = self.invoice

        # Test doc type is same as the journal when out_invoice
        document_type = invoice.journal_id.l10n_cr_edi_document_type
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.get_cyberfuel_doc_type(), document_type)

        # Test doc type is '03' when out_refund
        invoice.move_type = 'out_refund'
        self.assertEqual(invoice.get_cyberfuel_doc_type(), '03')

        # Test Journal requires document type
        with self.assertRaises(ValidationError):
            invoice.move_type = 'out_invoice'
            invoice.journal_id.sudo().l10n_cr_edi_document_type = False
            invoice.get_cyberfuel_doc_type()

        # Test Journal requires active the cyberfuel_einvoice
        invoice = self.invoice
        invoice.journal_id.sudo().edi_format_ids = False
        invoice.action_post()
        self.assertEqual('posted', invoice.state, 'State not posted.')

    def test_03_validate_invoice(self):
        """Test for Validation Invoice and sign of XML"""
        with freeze_time(self.frozen_today):
            invoice = self.invoice
            invoice.invoice_date = self.frozen_today

            # Test invoice is signed
            invoice.action_post()
            self.invoice.edi_document_ids.sudo().with_context(edi_test_mode=False).search(
                [('state', 'in', ['to_send', 'to_cancel'])])._process_documents_web_services()

            self.assertIn(invoice.l10n_cr_edi_sat_status, ['signed', 'accepted'], invoice.message_ids.mapped("body"))
            self.assertEqual(invoice.state, "posted", invoice.message_ids.mapped("body"))

            # Test amout in letters with invoice Total 9040.0 CRC
            amount_to_text = 'Nine Thousand And Forty with 00/100 (Colons)'
            self.assertEqual(invoice.l10n_cr_edi_amount_to_text(), amount_to_text, invoice.message_ids.mapped("body"))

            # Test Document request by full number
            invoice.l10n_cr_edi_full_number = '50618042000310157803099915872015126049001113967758'
            invoice.l10n_cr_edi_xml_filename = ''
            invoice.l10n_cr_edi_document_request()
            self.assertNotEqual(invoice.l10n_cr_edi_xml_filename, '')
            self.assertIsNotNone(invoice.l10n_cr_edi_xml_binary)

            # Test Answer Request
            invoice.l10n_cr_edi_full_number = '50601112000310157803099916042015242598001156873488'
            invoice.l10n_cr_edi_sat_status = 'none'
            invoice.l10n_cr_edi_answer_request()
            self.assertEqual(invoice.l10n_cr_edi_sat_status, 'accepted', invoice.message_ids.mapped("body"))

            # Test Answer Rejected
            invoice.l10n_cr_edi_full_number = '50626062000310157803099915931029818541002137122975'
            invoice.l10n_cr_edi_sat_status = 'none'
            invoice.l10n_cr_edi_answer_request()
            self.assertEqual(invoice.l10n_cr_edi_sat_status, 'rejected', invoice.message_ids.mapped("body"))

            # Test Electronic Export Invoice
            export_invoice = self.invoice
            export_invoice.write({
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_other_charges.id,
                    'price_unit': 450.0,
                    'quantity': 1,
                })]
            })

            other_charges_lines = export_invoice.invoice_line_ids.filtered(
                lambda l: l.product_id.categ_id == self.env.ref('l10n_cr_edi.product_category_other_charges')
            )
            self.assertEqual(len(other_charges_lines), 1, export_invoice.message_ids.mapped("body"))

            dict_invoice = export_invoice.edi_document_ids.edi_format_id._l10n_cr_edi_get_invoice_xml_values(
                export_invoice)
            self.assertTrue('totalotroscargos' in dict_invoice.get('resumen'))
            self.assertTrue('otroscargos' in dict_invoice)

    def test_04_validate_invoice_line(self):
        invoice = self.invoice
        line = invoice.invoice_line_ids[0]

        # Test product as other charges
        with self.assertRaisesRegex(UserError, "You need to define an 'CABYS code'*"):
            line.product_id.sudo().l10n_cr_edi_code_cabys_id = False
            invoice.action_post()

            # Test invoice is signed
            line.sudo().product_id = self.product_other_charges
            invoice.action_post()
            self.invoice.edi_document_ids.sudo().with_context(edi_test_mode=False).search(
                [('state', 'in', ['to_send', 'to_cancel'])])._process_documents_web_services()

    def test_05_invoice_addenda(self):
        with freeze_time(self.frozen_today):
            invoice = self.invoice
            invoice.invoice_date = self.frozen_today
            invoice.x_l10n_cr_edi_addenda = '1111|2222|3333|2021-01-01|4444'

            # Setup an addenda on the partner.
            invoice.partner_id.l10n_cr_edi_addenda = self.env.ref('l10n_cr_edi.gs1')

            self.invoice.action_post()
            json_addenda = self.invoice.edi_document_ids.edi_format_id._l10n_cr_edi_append_addenda(
                invoice, invoice.partner_id.l10n_cr_edi_addenda)
            self.assertEqual(
                json_addenda.get('compra_entrega').get('numerovendedor'), '1111', invoice.message_ids.mapped("body"))
            self.assertEqual(
                json_addenda.get('compra_entrega').get('fechaorden'), '2021-01-01')

    def test_006_electronic_purchase_invoice(self):
        """The electronic purchase invoice is a document that supports the purchase of goods or services
        to taxpayers who do not make use of edi documents (Simplified regime). This kind of invoice must
        be issued by the buyers and sent to DGT as receiver."""
        with freeze_time(self.frozen_today):
            purchase_invoice = self.purchase_invoice
            purchase_invoice.invoice_date = self.frozen_today

            invoice_data = self.purchase_invoice.edi_document_ids.edi_format_id._l10n_cr_edi_get_invoice_xml_values(
                purchase_invoice)
            # Test Issuer is provider
            self.assertEqual(invoice_data['emisor']['identificacion']['numero'], '123456789')
            # Test receiver is the Company
            self.assertEqual(invoice_data['receptor']['identificacion']['numero'], '3101578030')
