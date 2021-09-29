from odoo import fields, models, api


class ModelName(models.Model):
    _inherit = 'account.move'

    def create(self):
        pass
