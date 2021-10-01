# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from typing import Text
from odoo import api, models, fields, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_tilopay.controllers.main import TilopayController
from werkzeug import urls
import requests
import simplejson as json

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

LIST_PROVIDER = [('tilopay',_('Tilopay'))]
URL_PAYMENT = "https://app.tilopay.com/api/v1/processPayment"
URL_RETURN_STORE = "/shop/payment"

class PaymentTilopay(models.Model):
    _inherit = 'payment.acquirer'
    
    provider = fields.Selection(selection_add=LIST_PROVIDER,
                    ondelete={'tilopay': 'set default'})

    tilopay_email_account = fields.Char(String='Email Account')
    tilopay_password_account = fields.Char(String='Password')
    tilopay_key_account = fields.Char(String='Key')

    def tilopay_form_generate_values(self, values):
        base_url = self.get_base_url()
        tilopay_tx_values = dict(values)
        url_payment_tilopay = self.get_url_payment(values)
        if not url_payment_tilopay:
            raise UserError(_('Connection issues.'))
        tilopay_tx_values.update({
            'url_payment': url_payment_tilopay
        })      
        return tilopay_tx_values

    def get_url_payment(self, values):
        base_url = self.get_base_url()
        token = self.env["bt.payment.tilopay.token"].get_token(self.tilopay_email_account, self.tilopay_password_account)
        
        if token:
            json_payment = {
                "redirect" : urls.url_join(base_url, TilopayController._confirmation_url),#URL_RETURN_STORE
                "key": self.tilopay_key_account,
                "amount": values['amount'],
                "currency": values['currency'] and values['currency'].name or '',
                "billToFirstName": values.get('partner_first_name'),
                "billToLastName": values.get('partner_last_name'),
                "billToAddress": values.get('partner_address'),
                "billToAddress2": "",
                "billToCity": values.get('partner_city'),
                "billToState": values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
                "billToZipPostCode": values.get('partner_zip'),
                "billToCountry": values.get('partner_country') and values.get('partner_country').code or '',
                "billToTelephone": values.get('partner_phone'),
                "billToEmail": values.get('partner_email'),
                "orderNumber": values['reference'],
                "capture": "1",
                "subscription": "0"
            }
            headers = {
                'Authorization': '%s' % token,
                'Accept':'application/json',
                'Content-Type':'application/json'
                }
            resp = requests.post(URL_PAYMENT, headers=headers, json=json_payment)
            if resp.ok:
                js_html = json.loads(resp._content)
                return js_html["url"]
            else:
                return False        
        return False

    def tilopay_compute_fees(self, amount, currency_id, country_id):
        # print("tilopay_compute_fees")
        return amount

    def tilopay_get_form_action_url(self):
        self.ensure_one()
        return '/payment/tilopay/view'
    
class PaymentTransactionTilopay(models.Model):
    _inherit = 'payment.transaction'

    tilopay_code = fields.Char(string='Code')
    tilopay_description = fields.Char(string='Description')
    tilopay_auth = fields.Char(string='Auth')
    tilopay_order = fields.Char(string='Order')
    tilopay_crd = fields.Char(string='CRD')
    tilopay_padded = fields.Char(string='Padded')
    tilopay_authorization = fields.Char(string='Authorization')
    tilopay_brand = fields.Char(string='Brand')
    tilopay_last_digits = fields.Char(string='Last digits')
    tilopay_gateway_transaction = fields.Char(string='Gateway transaction')
    tilopay_tp_transaction = fields.Char(string='Tilopay transaction')

    def _tilopay_form_get_tx_from_data(self, data):
        reference = data.get("order")
        tx = self.env["payment.transaction"].search([
            ('reference','=',reference)
        ])
        return tx

    def _tilopay_form_validate(self, data):
        code = data.get('code')
        # code = "3"
        if code == '1':
            self._tilopay_data_write(data)
            #self.write({'acquirer_reference': data.get("order")})
            self._set_transaction_done()
            return False
        elif code == '2' or code == '3':
            error = _("Tilopay: %s") % (_("Denied") if code == '2' else _("Rejected"))
            self._tilopay_data_write(data)
            # self.write({'acquirer_reference': data.get("order")})
            _logger.info(error)
            self.write({'state_message': error})  
            # self._set_transaction_cancel()
            self._set_transaction_error(error)  
            return False
        else:
            error = _("Tilopay: %s") % (_("Internal error - unknown code (%s)") % data.get("code"))
            _logger.info(error)
            self.write({'state_message': error})
            self._set_transaction_error(error)        
        # _set_transaction_done _pending _cancel
            return False

    def _tilopay_data_write(self, data):
        self.write({
            'acquirer_reference': data.get("order"),
            'date': datetime.now(),
            'tilopay_code': data.get("code"),
            'tilopay_description': data.get("description"),
            'tilopay_auth': data.get("auth"),
            'tilopay_order': data.get("order"),
            'tilopay_crd': data.get("crd"),
            'tilopay_padded': data.get("padded"),
            'tilopay_authorization': data.get("authorization"),
            'tilopay_brand': data.get("brand"),
            'tilopay_last_digits': data.get("last-digits"),
            'tilopay_gateway_transaction': data.get("gateway-transaction"),
            'tilopay_tp_transaction': data.get("tilopay-transaction")
        })
