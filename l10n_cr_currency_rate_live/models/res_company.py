import datetime
import requests
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(selection_add=[('bccr', 'Bank of Costa Rica')])

    @api.model
    def set_special_defaults_on_install(self):
        all_companies = self.env['res.company'].search([])
        res = super(ResCompany, self).set_special_defaults_on_install()
        for company in all_companies.filtered(lambda comp: comp.country_id.code == 'CR'):
            # Bank of Costa Rica
            company.currency_provider = 'bccr'
        return res

    def _parse_bccr_data(self, available_currencies):
        """Costa Rica Bank
        Source: https://paper.dropbox.com/doc/API-Ministerio-de-Hacienda-znrOU6bGjTHcXjo8oUmBj
        Returned values from https://api.hacienda.go.cr/indicadores/tc
            {
            "dolar": {
                "venta": {
                "fecha": "2020-06-17 00:00:00",
                "valor": 577.79
                },
                "compra": {
                "fecha": "2020-06-17 00:00:00",
                "valor": 571.33
                }
            },
            "euro": {
                "fecha": "2020-06-17T00:00:00-06:00",
                "dolares": 1.1217,
                "colones": 648.11
            }
            }
        """
        available_currency_names = available_currencies.mapped('name')
        rslt = {'CRC': (1.0, fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))}
        if 'CRC' not in available_currency_names:
            return rslt
        url = "https://api.hacienda.go.cr/indicadores/tc"
        try:
            res = requests.get(url)
            res.raise_for_status()
            series = res.json()
            if 'USD' in available_currency_names:
                date_rate_str = series['dolar']['venta']['fecha']
                rate = 1.0 / float(series['dolar']['venta']['valor'])
                dtfmt_usd = '%Y-%m-%d %H:%M:%S'
                date_rate = datetime.datetime.strptime(date_rate_str, dtfmt_usd).strftime(DEFAULT_SERVER_DATE_FORMAT)
                rslt['USD'] = (rate, date_rate)
            if 'EUR' in available_currency_names:
                date_rate_str = series['euro']['fecha']
                rate = 1.0 / float(series['euro']['colones'])
                dtfmt_eur = '%Y-%m-%dT%H:%M:%S-06:00'
                date_rate = datetime.datetime.strptime(date_rate_str, dtfmt_eur).strftime(DEFAULT_SERVER_DATE_FORMAT)
                rslt['EUR'] = (rate, date_rate)
        except:  # noqa: E722 # pylint: disable=bare-except
            return rslt
        return rslt
