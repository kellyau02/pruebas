# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

import base64

from os.path import join
from lxml import objectify
from odoo.tools import misc

from odoo.addons.l10n_cr_edi.tests.test_l10n_cr_edi_invoice import TestCREdiCommon


class TestL10CREdiDocumentWorkflow(TestCREdiCommon):
    def setUp(self):
        super().setUp()
        self.company = self.env.user.company_id
        self.company.sudo().write(
            {'l10n_cr_edi_economic_activity_ids': [
                (6, 0, [self.env.ref('l10n_cr_edi.company_activity_361004').id])
            ]})
        self.invoice_model = self.env['account.move']
        self.rule = self.env.ref('l10n_edi_document.edi_document_rule')
        self.invoice_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'invoice.xml')).read().encode('UTF-8')
        self.no_economic_activity_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'no_economic_activity.xml'
        )).read().encode('UTF-8')
        self.same_name_1_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'same_name_1.xml')).read().encode('UTF-8')
        self.same_name_2_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'same_name_2.xml')).read().encode('UTF-8')
        self.finance_folder = self.env.ref('documents.documents_finance_folder')

    def test_xml2record(self):
        """The invoice must be generated based in the xml attached file.
        """
        invoice_type = 'out_invoice'
        # New journal having a foreign currency set.
        journal = self.env['account.move'].with_context({'default_move_type': invoice_type})._get_default_journal()

        create_values = {
            'move_type': invoice_type,
            'journal_id': journal.id,
        }

        invoice = self.env['account.move'].create(create_values)
        invoice.name = '/'
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
        })

        attachment.write({
            'res_model': 'account.move',
            'res_id': invoice.id,
        })
        invoice.xml2record()
        self.assertEqual(invoice.state, 'posted', invoice.message_ids.mapped("body"))

    def test_ir_attachment(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
        })
        # Test l10n_edi_document_is_xml() method

        # Must return lxml.objectify because is a valid XML for l10n_cr
        res = attachment.l10n_edi_document_is_xml()
        self.assertIsInstance(res, objectify.ObjectifiedElement)

        new_xml = self.invoice_xml.replace(b'ResumenFactura', b'Resumen')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })

        # Must return False because is an XML without ResumenFactura node
        res = attachment.l10n_edi_document_is_xml()
        self.assertFalse(res, 'This Document is not a valid EDI Document. Node ResumenFactura is missing')

        # Must return False because is an XML without  node
        new_xml = self.invoice_xml.replace(b'Emisor', b'Company')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })
        res = attachment.l10n_edi_document_is_xml()
        self.assertFalse(res, 'This Document is not a valid EDI Document. Node Emisor is missing')

        # Must return False because is an XML without NumeroConsecutivo node
        new_xml = self.invoice_xml.replace(b'NumeroConsecutivo', b'Numero')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })
        res = attachment.l10n_edi_document_is_xml()
        self.assertFalse(res, 'This Document is not a valid EDI Document. Node NumeroConsecutivo is missing')

        # Must return False because is an XML without Clave node
        new_xml = self.invoice_xml.replace(b'Clave', b'NumeroCompleto')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })
        res = attachment.l10n_edi_document_is_xml()
        self.assertFalse(res, 'This Document is not a valid EDI Document. Node Clave is missing')

        # Must return False because is an XML without a valid Namespace
        new_xml = self.invoice_xml.replace(b'cdn.comprobanteselectronicos.go.cr', b'vauxoo.com')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })
        res = attachment.l10n_edi_document_is_xml()
        self.assertFalse(res, 'This Document is not a valid EDI Document. Incorrect Namespace')

        # Test l10n_edi_document_type()

        # Test l10n_edi_document_type() with a valid XML for company as vendor
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
        })
        res = attachment.l10n_edi_document_type()
        self.assertEqual(res, ['vendorI', 'account.move'], "It's an Invoice for a vendor")

        # Test l10n_edi_document_type() with a country not allowed
        new_xml = self.invoice_xml.replace(b'cdn.comprobanteselectronicos.go.cr', b'vauxoo.com')
        attachment.company_id.country_id = self.env.ref('base.us')
        res = attachment.l10n_edi_document_type()
        attachment.company_id.country_id = self.env.ref('base.cr')
        self.assertEqual(res, ['', ''], "It's an Invoice for a vendor")

        # Test l10n_edi_document_type() Unabled to find Company vat partner
        new_xml = self.invoice_xml.replace(b'3101578030', b'1234567890')
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(new_xml),
        })
        res = attachment.l10n_edi_document_type()
        self.assertEqual(res, ['', ''], "It's an Invoice for a vendor")

    def test_other_charges(self):
        """The invoice must be generated with other charges"""
        invoice_type = 'in_invoice'
        # New journal having a foreign currency set.
        journal = self.env['account.move'].with_context({'default_move_type': invoice_type})._get_default_journal()

        create_values = {
            'move_type': invoice_type,
            'journal_id': journal.id,
        }

        invoice = self.env['account.move'].create(create_values)
        self.invoice_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'other_charges.xml')).read().encode('UTF-8')
        self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })
        invoice.xml2record()
        self.assertEqual(invoice.state, 'posted', invoice.message_ids.mapped("body"))
        self.assertEqual(invoice.l10n_cr_edi_xml_customer_binary_to_str(
            self.invoice_xml).ResumenFactura.TotalComprobante, invoice.amount_total,
            'Invoice total != TotalComprobante')

    def test_rounding_adjustment(self):
        """The invoice must be generated with rounding adjustment new line"""
        invoice_type = 'out_invoice'
        # New journal having a foreign currency set.
        journal = self.env['account.move'].with_context({'default_move_type': invoice_type})._get_default_journal()

        create_values = {
            'move_type': invoice_type,
            'journal_id': journal.id,
        }

        invoice = self.env['account.move'].create(create_values)
        invoice.name = '/'
        self.invoice_xml = misc.file_open(join(
            'l10n_cr_edi_document', 'tests', 'rounding_adjustment.xml')).read().encode('UTF-8')
        self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })
        invoice.xml2record()
        self.assertEqual(invoice.state, 'posted', invoice.message_ids.mapped("body"))
        self.assertEqual(invoice.l10n_cr_edi_xml_customer_binary_to_str(
            self.invoice_xml).ResumenFactura.TotalComprobante, invoice.amount_total,
            'Invoice total != TotalComprobante')

    def test_edi_document(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.invoice_xml),
        })
        invoice_document = self.env['documents.document'].create({
            'name': attachment.name,
            'folder_id': self.finance_folder.id,
            'attachment_id': attachment.id,
        })
        self.assertTrue(self.rule.create_record(invoice_document).get('res_id'), 'Invoice not generated.')

    def test_xml2record_without_economic_activity(self):
        invoice_type = 'out_invoice'
        # New journal having a foreign currency set.
        journal = self.env['account.move'].with_context({'default_move_type': invoice_type})._get_default_journal()
        create_values = {
            'move_type': invoice_type,
            'journal_id': journal.id,
        }

        invoice = self.env['account.move'].create(create_values)
        invoice.name = '/'
        self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.no_economic_activity_xml),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })
        invoice.xml2record()
        self.assertEqual(invoice.state, 'draft', invoice.message_ids.mapped("body"))
        self.assertTrue(
            '<p>Economic activity not found. Please check the Economic Activities configuration.</p>' in
            invoice.message_ids.mapped("body"), invoice.message_ids.mapped("body"))

    def test_xml_record_same_name_from_different_vendors(self):
        invoice_type = 'in_invoice'
        # New journal having a foreign currency set.
        journal = self.env['account.move'].with_context({'default_move_type': invoice_type})._get_default_journal()

        create_values = {
            'move_type': invoice_type,
            'journal_id': journal.id,
        }

        invoice = self.env['account.move'].create(create_values)
        invoice.name = '/'
        self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.same_name_1_xml),
            'res_model': 'account.move',
            'res_id': invoice.id,
        })
        invoice.xml2record()
        self.assertEqual(invoice.name, '00100001010000004231', invoice.message_ids.mapped("body"))

        invoice2 = invoice.copy({'partner_id': False})
        invoice2.name = '/'
        self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'datas': base64.b64encode(self.same_name_2_xml),
            'res_model': 'account.move',
            'res_id': invoice2.id,
        })
        invoice2.xml2record()
        self.assertEqual(invoice2.name, '00100001010000004231/001', invoice.message_ids.mapped("body"))
