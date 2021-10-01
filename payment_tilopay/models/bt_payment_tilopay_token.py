# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import requests
import simplejson as json

URL = "https://app.tilopay.com/api/v1/login"

class bt_payment_tilopay_token(models.Model):
    _name = "bt.payment.tilopay.token"
    _description = "BT - Payment Tilopay - Token"
    _rec_name = "token"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, 
                    index=True, default=lambda self: self.env.company)

    token = fields.Char(string='Nombre', required=True)
    expires_in = fields.Integer(string='Nombre', required=True)

    date = fields.Datetime(string='Date Create')
    date_expire = fields.Datetime(string='Date Expire')

    def get_token(self, email, password):
        id = self.search([('date_expire','>', datetime.now())], order="id desc", limit=1)
        # id = False
        if not id:
            data = {
                "email":email,
                "password":password
            }
            resp = requests.post(URL, data=data)
            if resp.ok:
                js = json.loads(resp._content)
                date_expire = datetime.now() + timedelta(seconds=(js["expires_in"]-300))
                datetime.now()
                id = self.create({
                    'token':js["access_token"],
                    'expires_in':js["expires_in"],
                    'date':datetime.now(),
                    'date_expire':date_expire
                })
            else:
                raise UserError(_('Problemas de conexion.'))
        return "bearer %s" % id.token