from odoo.tests.common import TransactionCase


class CurrencyTestCase(TransactionCase):

    def setUp(self):
        super(CurrencyTestCase, self).setUp()
        # Each test will check the number of rates for USD
        self.currency_usd = self.env.ref('base.USD')
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.currency_usd.id,
        })

    def test_live_currency_update_bccr(self):
        crc = self.env.ref('base.CRC')
        crc.active = True
        crc.rate_ids.unlink()
        usd = self.env.ref('base.USD')
        usd.active = True
        usd.rate_ids.unlink()
        self.test_company.write({
            'currency_provider': 'bccr',
            'currency_id': crc.id
        })
        crc_rates_count = len(crc.rate_ids)
        usd_rates_count = len(usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(crc.rate_ids), crc_rates_count + 1)
        self.assertEqual(crc.rate_ids[-1].rate, 1.0)
        self.assertEqual(len(usd.rate_ids), usd_rates_count + 1)
        self.assertLess(usd.rate_ids[-1].rate, 1)
