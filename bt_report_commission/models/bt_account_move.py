# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class bt_account_move(models.Model):  
    _inherit = "account.move"

    # @api.model
    # def create(self, vals):
    #     resp = super(bt_account_move, self).create(vals)

    #     for x in resp.invoice_line_ids:
    #         self.env['bt.rpt.cmn.account.line.calculator'].create({
    #             'account_line_id':x.id
    #         })

    #     return resp

    def action_post(self):
        resp = super(bt_account_move, self).action_post()

        for _self in self:
            for x in _self.invoice_line_ids:
                self.env['bt.rpt.cmn.account.line.calculator'].create({
                    'account_line_id':x.id
                })

        return resp