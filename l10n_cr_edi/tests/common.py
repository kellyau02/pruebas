from datetime import date

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged

import datetime


@tagged('-at_install', 'post_install')
class TestCREdiCommon(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_cr.account_chart_template_0',
                   edi_format_ref='l10n_cr_edi.edi_fedgt_4_3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.frozen_today = datetime.datetime.now()

        cls.invoice_model = cls.env['account.move'].with_context(default_type='in_invoice')
        cls.tax_model = cls.env['account.tax']
        cls.account_settings = cls.env['res.config.settings']

        cls.account_settings.l10n_cr_edi_test_env = True

        cls.currency_data['currency'] = cls.env.ref('base.CRC')

        cls.company_data['company'].write({
            'l10n_cr_edi_tradename': 'ClearCorp S.A. Testing',
            'l10n_cr_edi_test_env': True,
            'l10n_cr_edi_client_api_key': '-I96Hb3Z_ed',
            'vat': '3101578030',
            'l10n_cr_edi_vat_type': '02',
            'phone': '+506 4000 2677',
            'street': 'Edificio Sigma, Oficentro Republic',
            'street2': 'Edificio A, 2do Piso',
            'email': 'factura.cr.pruebas@vauxoo.com',
            'country_id': cls.env.ref('base.cr').id,
            'currency_id': cls.env.ref('base.CRC').id,
            'state_id': cls.env.ref('base.state_SJ').id,
            'l10n_cr_edi_canton_id': cls.env.ref('l10n_cr_edi.canton_1_15').id,
            'l10n_cr_edi_district_id': cls.env.ref('l10n_cr_edi.distrito_1_15_01').id,
            'l10n_cr_edi_neighborhood_id': cls.env.ref('l10n_cr_edi.barrio_1_15_01_05').id,
            'l10n_cr_edi_economic_activity_ids': [(6, 0, [
                cls.env.ref('l10n_cr_edi.company_activity_361004').id,
                cls.env.ref('l10n_cr_edi.company_activity_361002').id,
            ])],
        })

        # ==== Business ====

        cls.tax_13_sale = cls.env['account.tax'].create({
            'name': 'IVA 13%',
            'amount_type': 'percent',
            'l10n_cr_edi_code': '01',
            'l10n_cr_edi_iva_code': '08',
            'amount': 13,
            'type_tax_use': 'sale',
        })

        cls.tax_13_purchase = cls.env['account.tax'].create({
            'name': 'IVA 13%',
            'amount_type': 'percent',
            'l10n_cr_edi_code': '01',
            'l10n_cr_edi_iva_code': '08',
            'amount': 13,
            'type_tax_use': 'purchase',
        })

        cls.product = cls.env.ref("product.product_product_3")

        cls.product = cls.env['product.product'].create({
            'name': 'product_cr',
            'weight': 2,
            'uom_po_id': cls.env.ref('uom.product_uom_kgm').id,
            'uom_id': cls.env.ref('uom.product_uom_kgm').id,
            'lst_price': 1000.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'l10n_cr_edi_code_cabys_id': cls.env.ref('l10n_cr_edi_product_cabys.prod_cabys_0111100000100').id,
            'l10n_cr_edi_uom_id': cls.env.ref('l10n_cr_edi.uom_unidad').id,
        })

        cls.product_other_charges = cls.env.ref("l10n_cr_edi.product_other_charges_exportacion")

        cls.partner_a.write({
            'country_id': cls.env.ref('base.cr').id,
            'state_id': cls.env.ref('base.state_SJ').id,
            'l10n_cr_edi_canton_id': cls.env.ref('l10n_cr_edi.canton_1_01').id,
            'l10n_cr_edi_district_id': cls.env.ref('l10n_cr_edi.distrito_1_05_01').id,
            'l10n_cr_edi_neighborhood_id': cls.env.ref('l10n_cr_edi.barrio_1_01_04_01').id,
            'street': 'Calle El Agua, Esquina La Fe',
            'street2': 'Edif. Vida, Piso 3',
            'phone': '+506 2411 2233',
            'mobile': '',
            'email': 'noreply@example.com',
            'l10n_cr_edi_vat_type': '01',
            'zip': 39301,
            'vat': '123456789',
        })

        cls.company_data['default_journal_bank'].write({
            'type': 'sale',
            'code': 'FECR',
            'l10n_cr_edi_document_type': '01',
            'l10n_cr_edi_location': 1,
            'l10n_cr_edi_terminal': 1,
            'refund_sequence': True,
            'edi_format_ids': [(6, 0, cls.env.ref('l10n_cr_edi.edi_fedgt_4_3').ids)],
        })

        cls.company_data['default_journal_purchase'].write({
            'type': 'purchase',
            'code': 'FEECR',
            'l10n_cr_edi_document_type': '08',
            'l10n_cr_edi_location': 1,
            'l10n_cr_edi_terminal': 1,
            'refund_sequence': True,
            'edi_format_ids': [(6, 0, cls.env.ref('l10n_cr_edi.edi_fedgt_4_3').ids)],
        })

        cls.invoice = cls.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': date.today(),
            'currency_id': cls.currency_data['currency'].id,
            'journal_id': cls.company_data['default_journal_bank'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, (cls.tax_13_sale).ids)],
            })],
        })

        cls.purchase_invoice = cls.env['account.move'].with_context(edi_test_mode=True).create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2017-01-01',
            'date': date.today(),
            'currency_id': cls.currency_data['currency'].id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'price_unit': 2000.0,
                'quantity': 5,
                'discount': 20.0,
            })],
        })
