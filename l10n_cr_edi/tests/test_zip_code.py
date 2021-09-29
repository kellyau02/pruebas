from odoo.tests import Form
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('zipcode')
class TestContactZipCodeCase(TransactionCase):
    def test_01_l10n_cr_edi_zip_code(self):
        partner = self.env['res.partner']
        country = self.env.ref('base.cr')
        l10n_cr_edi_district = self.env.ref('l10n_cr_edi.distrito_1_05_02')

        # Test onchange zip code when district is set
        with Form(self.env['res.partner']) as form:
            form.name = 'Test parnert with zip code'
            form.country_id = country
            form.l10n_cr_edi_district_id = l10n_cr_edi_district
            partner = form.save()
        self.assertEqual(partner.zip, '10502')
