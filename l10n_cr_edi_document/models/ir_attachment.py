# Copyright 2020 Vauxoo
# License AGPL-3 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

from lxml import objectify
from odoo import api, models, _

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def l10n_edi_document_is_xml(self):
        self.ensure_one()
        super().l10n_edi_document_type()
        if not self.datas:
            return False

        schema = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/'
        res = True
        try:
            datas = base64.decodebytes(self.datas)
            xml = objectify.fromstring(datas)
        except (SyntaxError, ValueError):
            return False

        if not xml.nsmap or xml.nsmap[None][:60] != schema:
            res = False
        if not hasattr(xml, 'Clave'):
            res = False
        if not hasattr(xml, 'NumeroConsecutivo'):
            res = False
        if not hasattr(xml, 'FechaEmision'):
            res = False
        if not hasattr(xml, 'Emisor'):
            res = False
        if not hasattr(xml, 'ResumenFactura'):
            res = False
        if not res:
            return res
        return xml

    def l10n_edi_document_type(self, document=False):
        self.ensure_one()
        res = super().l10n_edi_document_type()
        if self.company_id.country_id != self.env.ref('base.cr'):
            return res
        document_id = self.env['documents.document'].search([('attachment_id', '=', self.id)])
        xml = self.l10n_edi_document_is_xml()
        if not xml:
            if document_id:
                document_id.message_post(body=_('This Document is not a valid EDI Document.'))
            return ['', '']
        vat = self.company_id.vat
        document_type = 'customer' if xml['Emisor']['Identificacion']['Numero'].text == vat else (
            'vendor' if hasattr(xml['Receptor'], 'Identificacion') and
            xml['Receptor']['Identificacion']['Numero'].text == vat else False)
        if not document_type:
            if document_id:
                document_id.message_post(body=_(
                    'Neither the emitter nor the receiver of this XML is this '
                    'company, please review this document.'))
            return ['', '']
        cr_doc_type = {
            '01': 'I',
            '02': 'I',
            '09': 'I',
            '04': 'I',
            '03': 'E',
            '05': 'E',
            '06': 'E',
            '07': 'E',
            '08': 'E',
        }.get(xml['NumeroConsecutivo'].text[8:10])

        res_model = 'account.move'

        return [('%s%s' % (document_type, cr_doc_type)) if document_type else False, res_model]
