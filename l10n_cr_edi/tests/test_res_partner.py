from odoo.tests import Form, TransactionCase, tagged


@tagged('partner')
class TestResPartner(TransactionCase):

    def test_01_sugef_get(self):
        """Test - GET request to HACIENDA."""

        with self.assertRaises(AssertionError):
            partner_form = Form(self.env['res.partner'])
            partner_form.name = 'Test Name'
            partner_form.vat = '31015780'
            partner = partner_form.save()

        partner_form = Form(self.env['res.partner'])
        partner_form.name = 'Test Name'
        partner_form.vat = '3101578030'
        partner = partner_form.save()
        self.assertRecordValues(partner, [{
            'name': 'CLEARCORP, SOCIEDAD ANONIMA',
            'l10n_cr_edi_vat_type': '02',
        }])
