import re
from odoo import models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def generate_email(self, res_ids, fields):
        """ Method overridden in order to add an attachment containing the AHC
        to the draft message when opening the 'send by mail' wizard on an invoice.
        This attachment generation will only occur if the DGT required data are
        present on the invoice. Otherwise, no ISR attachment will be created, and
        the mail will only contain the invoice (as defined in the mother method).
        """
        result = super().generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        if self.model not in ['account.move']:
            return result

        records = self.env[self.model].browse(res_ids)
        for record in records:
            record_data = (result[record.id] if multi_mode else result)
            pattern = re.compile(r'^AHC-.*\.xml')
            for res in record.attachment_ids.filtered(lambda a: pattern.search(a.name)):
                record_data.setdefault('attachments', [])
                if not [att for att in record_data['attachments'] if res.name in att]:
                    record_data['attachments'].append((res.name, res.datas))

        return result
