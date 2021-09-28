# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError

from datetime import datetime

LIST_STATE = [
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ]

# commission_percentage_min
COMMISSION_PERCENTAGE_MIN = 30

class bt_account_line_report1(models.Model):
    _name = 'bt.account.line.report'
    _auto = False
    _description = 'Report - Account Line'
    _rec_name = 'name'
    _order = "date"

    # *** FIELDS VIEW ***

    id = fields.Integer(string='id', readonly=True)
    number = fields.Char(string="Number")
    date = fields.Date(string='Date')
    parent_state = fields.Selection(LIST_STATE, string='State')
    company_id = fields.Many2one('res.company', string='Company')
    company_currency_id = fields.Many2one('res.currency', string='Company - Currency')
    name = fields.Char(string="Name")
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Monetary(string='Price Unit', currency_field="currency_id")
    discount = fields.Float(string='Discount', currency_field="currency_id")
    price_subtotal = fields.Monetary(string='Price Subtotal', currency_field="currency_id")
    price_total = fields.Monetary(string='Price Total', currency_field="currency_id")
    price_total_currency_id = fields.Monetary(string='Price Total - Company Currency', currency_field="company_currency_id")
    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency')
    account_id = fields.Many2one('account.move', string='Account')
    account_line_id = fields.Many2one('account.move.line', string='Account Line')
    # amount_residual = fields.Many2one('account.move', string='Amount Residual')
    # invoice_payments_widget = fields.Many2one('account.move', string='Invoice Payments')

    account_id_user = fields.Many2one(related="account_id.invoice_user_id", string='User')

    commission_id = fields.Many2one('bt.rpt.cmn.account.line.calculator', string='Report Commission')
    
    amount_commission = fields.Float(related='commission_id.amount_commission', string='Commision Amount')#, default=defau
    
    taxes_percentage = fields.Float(string='Taxes Percentage')

    run_commission = fields.Datetime(compute='_compute_run_commission', string='Run Commission')#, compute_sudo=True)    
    # percentage_commission = fields.Float(compute='_compute_amount_commission1', string='percentage_commission')#, compute_sudo=True)
    
    collaborator = fields.Many2one(related='commission_id.collaborator', string='collaborator')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    job = fields.Many2one(related='commission_id.job', string='job')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    profile = fields.Many2one(related='commission_id.profile', string='profile')#,  
                        # compute='_compute_amount_commission1', compute_sudo=True)
    category = fields.Many2one(related='commission_id.category', string='category')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    commission_percentage = fields.Float(related='commission_id.commission_percentage', string='Commission Percentage')

    product_id_categ = fields.Many2one(related='product_id.categ_id', string='Category')

    product_id_cost_unit = fields.Float(related='product_id.standard_price', groups="base.group_user", string='Cost Unit', currency_field="company_currency_id")

    utility_sale = fields.Float(related="commission_id.utility_sale", 
        string='Utility Sale', currency_field="company_currency_id")
    utility_percentage = fields.Float(related="commission_id.utility_percentage", 
        string='Utility Percentage')

    
    amount_payment = fields.Float(related="commission_id.amount_payment", 
        string='Payment Amount')
    percentage_payment = fields.Float(related="commission_id.percentage_payment", 
        string='Payment Percentage')
    total_payment = fields.Float(related="commission_id.total_payment", 
        string='Full Payment')
    commission_payment = fields.Float(related="commission_id.commission_payment", 
        string='Payment Commission')

    #        collaborator = fields.Many2one(related='product_id.categ_id', 'res.users', string='collaborator')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # job = fields.Many2one(related='product_id.categ_id', 'bt.commission.job', string='job')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # profile = fields.Many2one(related='product_id.categ_id', 'bt.commission.profile', string='profile')#,  
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # category = fields.Many2one(related='product_id.categ_id', 'bt.commission.category', string='category')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # commission_percentage = fields.Float(related='product_id.categ_id', string='Commission Percentage')

    def get_category(self, category_ids):
        category = False
        for x in category_ids:
            if self.product_id_categ.id in x.get_categ():
                category = x.id
                continue
        return category
        
    def get_job(self, commission_ids):
        job = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                job = x.job.id
                continue
        return job
        
    def get_profile(self, commission_ids):
        profile = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                profile = x.profile.id
                continue
        return profile

    def get_commission_percentage(self, commission_ids):
        commission_percentage = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                commission_percentage = x.commission_percentage
                continue
        return commission_percentage

    @api.depends('account_id_user')
    def _compute_run_commission(self):
        # commission_percentage_min = 30
        # profile_ids = False
        # category_ids = False
        # if 'profile' in self._context:
        #     profile_ids = self.env["bt.commission.profile"].browse(self._context['profile'])
        
        commission_ids = []
        if 'profile' in self._context and 'job' in self._context:
            commission_ids = self.env["bt.commission"].search([
                ('profile','=',self._context["profile"]),
                ('job','=',self._context["job"])
            ])

        category_ids = []
        if len(commission_ids):
            category_ids = self.env["bt.commission.category"].search([
                ('id','=',[x.category.id for x in commission_ids])
                ])

        for _self in self:
            # _self = _self.commission_id
            _self.commission_id.collaborator = False
            _self.commission_id.job = False
            _self.commission_id.profile = False
            _self.commission_id.category = False
            _self.commission_id.commission_percentage = 0
            _self.commission_id.amount_commission = 0

            # _self.percentage_commission = 0
            _self.run_commission = datetime.now()
            if 'amount_commission' in self._context:
                
                # if _self.account_id.state == 'draft':
                #     _self.account_id.invoice_date = datetime.now()
                
                _self.commission_id.collaborator = self._context["collaborator"] if 'collaborator' in _self._context else False
                _self.commission_id.profile = self._context["profile"] if 'profile' in _self._context else False
                _self.commission_id.job = self._context["job"] if 'job' in _self._context else False
                # _self.get_job(commission_ids) #                
                 #_self.get_profile(commission_ids) #self._context["profile"] if 'profile' in _self._context else False
                _self.commission_id.category = _self.get_category(category_ids) #self._context["category"] if 'category' in _self._context else False
               

                _self.commission_id.utility_sale = _self.price_total_currency_id - _self.product_id_cost_unit
                _self.commission_id.utility_percentage = (_self.commission_id.utility_sale / _self.price_total_currency_id) * 100 if _self.commission_id.utility_sale > 0 else 0
                
                commission_percentage = _self.get_commission_percentage(commission_ids)

                _self.commission_id.commission_percentage = ((_self.commission_id.utility_percentage * commission_percentage) / COMMISSION_PERCENTAGE_MIN) if _self.commission_id.utility_percentage < COMMISSION_PERCENTAGE_MIN else commission_percentage
                _self.commission_id.amount_commission = _self.price_total_currency_id * (_self.commission_percentage / 100)

                _self.commission_id.run_payment()

                print("%s => %s" % (_self.product_id_categ ,_self.commission_id.category))
                # _self.percentage_commission = self._context["amount_commission"]
                # _self.amount_commission1 = (_self.percentage_commission / 100) * _self.price_total_currency_id if _self.percentage_commission > 0 else 0
        # self.update()

    @api.model
    def default_get(self, fields_list):
        resp = super(bt_account_line_report, self).default_get(fields_list)
        resp["amount_commission"] = 5.6
        return resp

    def init(self):
        model = "bt_account_line_report"
        tools.drop_view_if_exists(self._cr, model)

        # self._cr.execute("""
        #     INSERT INTO bt_rpt_cmn_account_line_calculator (collaborator, job, profile, category)
        #         VALUES (1, 1, 1, 1)
        #     """)
        self._cr.execute("""
            SELECT * FROM account_move_line as am FULL JOIN
                bt_rpt_cmn_account_line_calculator as ra
                on ra.account_line_id = am.id
                    WHERE ra.id IS NULL
            """)

        ids = [r[0] for r in self._cr.fetchall()]

        if len(ids):
            for id in ids:
                self._cr.execute("""
                    INSERT INTO bt_rpt_cmn_account_line_calculator (account_line_id)
                        VALUES (%s)
                """ % id)

        self._cr.execute("""
            CREATE OR REPLACE VIEW """ + model + """ AS (
                SELECT 
                    v.id,
                    v.move_name as number,
                    v.date,
                    v.parent_state,
                    v.company_id,
                    v.company_currency_id,
                    v.name,
                    v.quantity,
                    v.price_unit,
                    v.discount,
                    v.price_subtotal,
                    v.price_total,
                    v.partner_id,
                    v.product_id,
                    v.currency_id,
                    v.credit + v.debit as price_total_currency_id,
                    v.move_id as account_id,
                    v.id as account_line_id,
                    c.id as commission_id,
                    ((v.price_total - v.price_subtotal) / v.price_subtotal) * 100 as taxes_percentage
                FROM public.account_move_line as v
                INNER JOIN public.bt_rpt_cmn_account_line_calculator as c
                ON c.account_line_id = v.id
                WHERE v.exclude_from_invoice_tab = false
            )""")


# ,
#                     c.amount_commission as amount_commission,
#                     c.category as category,
#                     c.profile as profile,
#                     c.job as job,
#                     c.collaborator as collaborator
#                     c.commission_percentage as commission_percentage                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError

from datetime import datetime

LIST_STATE = [
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ]

# commission_percentage_min
COMMISSION_PERCENTAGE_MIN = 30

class bt_account_line_report1(models.Model):
    _name = 'bt.account.line.report'
    _auto = False
    _description = 'Report - Account Line'
    _rec_name = 'name'
    _order = "date"

    # *** FIELDS VIEW ***

    id = fields.Integer(string='id', readonly=True)
    number = fields.Char(string="Number")
    date = fields.Date(string='Date')
    parent_state = fields.Selection(LIST_STATE, string='State')
    company_id = fields.Many2one('res.company', string='Company')
    company_currency_id = fields.Many2one('res.currency', string='Company - Currency')
    name = fields.Char(string="Name")
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Monetary(string='Price Unit', currency_field="currency_id")
    discount = fields.Float(string='Discount', currency_field="currency_id")
    price_subtotal = fields.Monetary(string='Price Subtotal', currency_field="currency_id")
    price_total = fields.Monetary(string='Price Total', currency_field="currency_id")
    price_total_currency_id = fields.Monetary(string='Price Total - Company Currency', currency_field="company_currency_id")
    partner_id = fields.Many2one('res.partner', string='Partner')
    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency')
    account_id = fields.Many2one('account.move', string='Account')
    account_line_id = fields.Many2one('account.move.line', string='Account Line')
    # amount_residual = fields.Many2one('account.move', string='Amount Residual')
    # invoice_payments_widget = fields.Many2one('account.move', string='Invoice Payments')

    account_id_user = fields.Many2one(related="account_id.invoice_user_id", string='User')

    commission_id = fields.Many2one('bt.rpt.cmn.account.line.calculator', string='Report Commission')
    
    amount_commission = fields.Float(related='commission_id.amount_commission', string='Commision Amount')#, default=defau
    
    taxes_percentage = fields.Float(string='Taxes Percentage')

    run_commission = fields.Datetime(compute='_compute_run_commission', string='Run Commission')#, compute_sudo=True)    
    # percentage_commission = fields.Float(compute='_compute_amount_commission1', string='percentage_commission')#, compute_sudo=True)
    
    collaborator = fields.Many2one(related='commission_id.collaborator', string='collaborator')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    job = fields.Many2one(related='commission_id.job', string='job')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    profile = fields.Many2one(related='commission_id.profile', string='profile')#,  
                        # compute='_compute_amount_commission1', compute_sudo=True)
    category = fields.Many2one(related='commission_id.category', string='category')#, 
                        # compute='_compute_amount_commission1', compute_sudo=True)
    commission_percentage = fields.Float(related='commission_id.commission_percentage', string='Commission Percentage')

    product_id_categ = fields.Many2one(related='product_id.categ_id', string='Category')

    product_id_cost_unit = fields.Float(related='product_id.standard_price', groups="base.group_user", string='Cost Unit', currency_field="company_currency_id")

    utility_sale = fields.Float(related="commission_id.utility_sale", 
        string='Utility Sale', currency_field="company_currency_id")
    utility_percentage = fields.Float(related="commission_id.utility_percentage", 
        string='Utility Percentage')

    
    amount_payment = fields.Float(related="commission_id.amount_payment", 
        string='Payment Amount')
    percentage_payment = fields.Float(related="commission_id.percentage_payment", 
        string='Payment Percentage')
    total_payment = fields.Float(related="commission_id.total_payment", 
        string='Full Payment')
    commission_payment = fields.Float(related="commission_id.commission_payment", 
        string='Payment Commission')

    #        collaborator = fields.Many2one(related='product_id.categ_id', 'res.users', string='collaborator')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # job = fields.Many2one(related='product_id.categ_id', 'bt.commission.job', string='job')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # profile = fields.Many2one(related='product_id.categ_id', 'bt.commission.profile', string='profile')#,  
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # category = fields.Many2one(related='product_id.categ_id', 'bt.commission.category', string='category')#, 
    #                     # compute='_compute_amount_commission1', compute_sudo=True)
    # commission_percentage = fields.Float(related='product_id.categ_id', string='Commission Percentage')

    def get_category(self, category_ids):
        category = False
        for x in category_ids:
            if self.product_id_categ.id in x.get_categ():
                category = x.id
                continue
        return category
        
    def get_job(self, commission_ids):
        job = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                job = x.job.id
                continue
        return job
        
    def get_profile(self, commission_ids):
        profile = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                profile = x.profile.id
                continue
        return profile

    def get_commission_percentage(self, commission_ids):
        commission_percentage = False
        for x in commission_ids:
            if self.category.id == x.category.id:
                commission_percentage = x.commission_percentage
                continue
        return commission_percentage

    @api.depends('account_id_user')
    def _compute_run_commission(self):
        # commission_percentage_min = 30
        # profile_ids = False
        # category_ids = False
        # if 'profile' in self._context:
        #     profile_ids = self.env["bt.commission.profile"].browse(self._context['profile'])
        
        commission_ids = []
        if 'profile' in self._context and 'job' in self._context:
            commission_ids = self.env["bt.commission"].search([
                ('profile','=',self._context["profile"]),
                ('job','=',self._context["job"])
            ])

        category_ids = []
        if len(commission_ids):
            category_ids = self.env["bt.commission.category"].search([
                ('id','=',[x.category.id for x in commission_ids])
                ])

        for _self in self:
            # _self = _self.commission_id
            _self.commission_id.collaborator = False
            _self.commission_id.job = False
            _self.commission_id.profile = False
            _self.commission_id.category = False
            _self.commission_id.commission_percentage = 0
            _self.commission_id.amount_commission = 0

            # _self.percentage_commission = 0
            _self.run_commission = datetime.now()
            if 'amount_commission' in self._context:
                
                # if _self.account_id.state == 'draft':
                #     _self.account_id.invoice_date = datetime.now()
                
                _self.commission_id.collaborator = self._context["collaborator"] if 'collaborator' in _self._context else False
                _self.commission_id.profile = self._context["profile"] if 'profile' in _self._context else False
                _self.commission_id.job = self._context["job"] if 'job' in _self._context else False
                # _self.get_job(commission_ids) #                
                 #_self.get_profile(commission_ids) #self._context["profile"] if 'profile' in _self._context else False
                _self.commission_id.category = _self.get_category(category_ids) #self._context["category"] if 'category' in _self._context else False
               

                _self.commission_id.utility_sale = _self.price_total_currency_id - _self.product_id_cost_unit
                _self.commission_id.utility_percentage = (_self.commission_id.utility_sale / _self.price_total_currency_id) * 100 if _self.commission_id.utility_sale > 0 else 0
                
                commission_percentage = _self.get_commission_percentage(commission_ids)

                _self.commission_id.commission_percentage = ((_self.commission_id.utility_percentage * commission_percentage) / COMMISSION_PERCENTAGE_MIN) if _self.commission_id.utility_percentage < COMMISSION_PERCENTAGE_MIN else commission_percentage
                _self.commission_id.amount_commission = _self.price_total_currency_id * (_self.commission_percentage / 100)

                _self.commission_id.run_payment()

                print("%s => %s" % (_self.product_id_categ ,_self.commission_id.category))
                # _self.percentage_commission = self._context["amount_commission"]
                # _self.amount_commission1 = (_self.percentage_commission / 100) * _self.price_total_currency_id if _self.percentage_commission > 0 else 0
        # self.update()

    @api.model
    def default_get(self, fields_list):
        resp = super(bt_account_line_report, self).default_get(fields_list)
        resp["amount_commission"] = 5.6
        return resp

    def init(self):
        model = "bt_account_line_report"
        tools.drop_view_if_exists(self._cr, model)

        # self._cr.execute("""
        #     INSERT INTO bt_rpt_cmn_account_line_calculator (collaborator, job, profile, category)
        #         VALUES (1, 1, 1, 1)
        #     """)
        self._cr.execute("""
            SELECT * FROM account_move_line as am FULL JOIN
                bt_rpt_cmn_account_line_calculator as ra
                on ra.account_line_id = am.id
                    WHERE ra.id IS NULL
            """)

        ids = [r[0] for r in self._cr.fetchall()]

        if len(ids):
            for id in ids:
                self._cr.execute("""
                    INSERT INTO bt_rpt_cmn_account_line_calculator (account_line_id)
                        VALUES (%s)
                """ % id)

        self._cr.execute("""
            CREATE OR REPLACE VIEW """ + model + """ AS (
                SELECT 
                    v.id,
                    v.move_name as number,
                    v.date,
                    v.parent_state,
                    v.company_id,
                    v.company_currency_id,
                    v.name,
                    v.quantity,
                    v.price_unit,
                    v.discount,
                    v.price_subtotal,
                    v.price_total,
                    v.partner_id,
                    v.product_id,
                    v.currency_id,
                    v.credit + v.debit as price_total_currency_id,
                    v.move_id as account_id,
                    v.id as account_line_id,
                    c.id as commission_id,
                    ((v.price_total - v.price_subtotal) / v.price_subtotal) * 100 as taxes_percentage
                FROM public.account_move_line as v
                INNER JOIN public.bt_rpt_cmn_account_line_calculator as c
                ON c.account_line_id = v.id
                WHERE v.exclude_from_invoice_tab = false
            )""")


# ,
#                     c.amount_commission as amount_commission,
#                     c.category as category,
#                     c.profile as profile,
#                     c.job as job,
#                     c.collaborator as collaborator
#                     c.commission_percentage as commission_percentage