from odoo import models


class WorkflowActionRuleAccount(models.Model):
    _inherit = ['documents.workflow.rule']

    def _prepare_invoice_data(self, document_type, document):
        values = super()._prepare_invoice_data(document_type, document)
        xml = document.attachment_id.l10n_edi_document_is_xml()
        if not xml:
            return values
        journal_domain = [
            ('type', '=', 'sale' if 'customer' in document_type else 'purchase'),
            ('edi_format_ids', '=', self.env.ref('l10n_cr_edi.edi_fedgt_4_3').id),
            ('l10n_cr_edi_document_type', '=', xml['Clave'].text[29:31]),
            ('l10n_cr_edi_location', '=', xml['Clave'].text[21:24].strip("0")),
            ('l10n_cr_edi_terminal', '=', xml['Clave'].text[24:29].strip("0")),
        ]
        journal = self.env['account.journal'].search(journal_domain, limit=1)
        if not journal:
            journal_domain = journal_domain[:1]
            journal = journal.search(journal_domain, limit=1)
        if journal:
            values['journal_id'] = journal.id
        return values
