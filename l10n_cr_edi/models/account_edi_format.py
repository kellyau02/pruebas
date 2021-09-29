import base64

import logging
import json
from odoo import api, models, _
from odoo.exceptions import ValidationError

from lxml.objectify import fromstring

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # FE: Helpers
    # -------------------------------------------------------------------------
    @api.model
    def _l10n_cr_edi_append_addenda(self, move, addenda):
        """ Append an additional block to the signed XML passed as parameter.
        :param move:    The account.move record.
        :param XML:    The invoice's JSON as a string.
        :param addenda: The addenda to add as a string.
        :return json:   The JSON including the addenda.
        """
        addenda_values = {'record': move}
        addenda = fromstring(addenda._render(values=addenda_values))
        if not addenda:
            return False
        json_addenda = {}
        json_addenda[addenda.tag] = {}
        for v in addenda.descendantpaths():
            dict_values = v.split('.')
            if len(dict_values) > 1:
                json_addenda[dict_values[0]][dict_values[1]] = str(addenda.find(dict_values[1]))

        move.message_post(
            body=_('Addenda has been added in the XML with success'))
        return json_addenda

    @api.model
    def _l10n_cr_edi_check_configuration(self, move):
        company = move.company_id
        pac_password = company.l10n_cr_edi_client_api_key

        errors = []

        # == Check the credentials to call the PAC web-service ==
        if not pac_password:
            errors.append(_('No PAC credentials specified.'))

        # == Check partner information ==
        partner = move.partner_id
        if partner.vat and not partner.l10n_cr_edi_vat_type:
            errors.append(_("VAT type is required when a VAT is set... Please check the partner's vat type."))

        address_fields = (
            partner.state_id,
            partner.l10n_cr_edi_canton_id,
            partner.l10n_cr_edi_district_id,
            partner.l10n_cr_edi_neighborhood_id, partner.street
        )
        check_addrs = partner.country_id == self.env.ref('base.cr') and any(address_fields) and not all(address_fields)
        if check_addrs:
            errors.append(
                _("If one address field is set, the full address is required. Please check the partner's address."))

        return errors

    @api.model
    def _l10n_cr_edi_format_error_message(self, error_title, errors):
        bullet_list_msg = ''.join('<li>%s</li>' % msg for msg in errors)
        return '%s<ul>%s</ul>' % (error_title, bullet_list_msg)

    # ----------------------------------------
    # XML Generation: Generic
    # ----------------------------------------
    def get_other_charges_info(self, invoice):
        other_charges = []
        charges_amount = 0.0
        lines = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id.categ_id == self.env.ref('l10n_cr_edi.product_category_other_charges'))
        for line in lines:
            other_charges.append(
                {
                    "tipodocumento": line.product_id.default_code,
                    "nombre": line.product_id.name,
                    "detalle": line.product_id.name,
                    "montocargo": line.price_unit * line.quantity,
                })
            charges_amount = charges_amount + line.price_unit * line.quantity
        return other_charges, charges_amount

    def _l10n_cr_edi_get_invoice_xml_values(self, invoice):
        """ Doesn't check if the config is correct so you need to call _l10n_mx_edi_check_config first.
        :param invoice:
        :return:
        """
        xml_values = {}
        invoice_totals, invoice_lines, other_charges = self.get_invoice_data(invoice)
        if other_charges:
            xml_values.update({'otroscargos': other_charges})

        invoice_sender = invoice.get_issuing_company_info()
        invoice_receiver = invoice.get_partner_info()
        if invoice.get_cyberfuel_doc_type() == '08':
            invoice_sender = invoice.get_partner_info()
            invoice_receiver = invoice.get_issuing_company_info()

        xml_values.update({
            'api_key': invoice.company_id.l10n_cr_edi_client_api_key,
            'encabezado': invoice.get_invoice_header(),
            'clave': invoice.get_invoice_key(),
            'emisor': invoice_sender,
            'receptor': invoice_receiver,
            'detalle': invoice_lines,
            'resumen': invoice_totals
        })

        comment = invoice.invoice_line_ids.filtered(
            lambda inv: inv.display_type).mapped('name')
        if comment:
            xml_values.update({
                'otros': [{
                    'codigo': 'Notas',
                    'texto': "\n".join(comment)
                }]
            })

        if invoice.l10n_cr_edi_ref_type:
            xml_values.update({
                'referencia': invoice.get_reference_information()
            })

        addenda = invoice.partner_id.l10n_cr_edi_addenda or \
            invoice.partner_id.commercial_partner_id.l10n_cr_edi_addenda
        if addenda:
            xml_values.update(self._l10n_cr_edi_append_addenda(invoice, addenda))
        return xml_values

    # -------------------------------------------------------------------------
    # CFDI Generation: Invoices
    # -------------------------------------------------------------------------

    def get_invoice_data(self, invoice):
        invoice_lines = []
        invoice_totals = {
            'totalserviciogravado': 0.0,
            'totalservicioexento': 0.0,
            'totalmercaderiagravado': 0.0,
            'totalmercaderiaexento': 0.0,
            'totalgravado': 0.0,
            'totalexento': 0.0,
            'totalventa': 0.0,
            'totaldescuentos': 0.0,
            'totalventaneta': 0.0,
            'totalimpuestos': 0.0,
            'totalcomprobante': 0.0,
            'totalivadevuelto': 0.0,
        }
        invoice_exonerated = {
            'totalservicioexonerado': 0.0,
            'totalmercaderiaexonerado': 0.0,
            'totalexonerado': 0.0,
        }
        currency = self.env.context.get('force_currency') or invoice.currency_id
        invoice_totals.update({
            'moneda': currency.name,
            'tipo_cambio': invoice.l10n_cr_currency_rate
        })

        other_charges, charges_amount = self.get_other_charges_info(invoice)
        if other_charges:
            invoice_totals.update({
                'totalotroscargos': charges_amount,
                'totalcomprobante': invoice_totals['totalcomprobante'] + charges_amount
            })

        for line in invoice.invoice_line_ids.filtered(
                lambda inv: not inv.display_type and inv.price_unit and
                inv.product_id.categ_id != self.env.ref('l10n_cr_edi.product_category_other_charges')):
            line_data = {
                'numero': len(invoice_lines) + 1,
                'codigo_hacienda': line.product_id.l10n_cr_edi_code_cabys_id.code or ''
            }

            if invoice.get_cyberfuel_doc_type() == '09':
                if line.product_id.l10n_cr_edi_tariff_heading:
                    line_data.update({
                        'partida': line.product_id.l10n_cr_edi_tariff_heading})
                elif line.product_id.l10n_cr_edi_uom_id.uom_type != 'service':
                    raise ValidationError(_(
                        'The product must have a tariff heading '
                        'in Invoices for export'))

            if line.product_id.default_code:
                line_data.update({
                    'codigo': line.product_id.default_code,
                    'tipo': '04',
                    # FIXME Add the different product codes from D.G.T.
                })

            # Calculate the discount by rouding the line discounted value
            # first because Odoo does it like this, otherwise there are
            # rounding errors
            subtotal_before_discount = line.price_unit * line.quantity
            line_data.update({
                'cantidad': line.quantity,
                'unidad_medida': line.product_id.l10n_cr_edi_uom_id.code or 'Unid',
                'unidad_medida_comercial': line.product_id.uom_id.name,
                'detalle': (len(line.name) > 160 and
                            line.name[:156] + '...' or line.name),
                'precio_unitario': line.price_unit,
                'monto_total': round(subtotal_before_discount, 5)
            })

            discount = 0.0
            if line.discount:
                discount = round(
                    subtotal_before_discount * line.discount / 100, 5)
                line_data.update({'descuento': [{
                    'monto': discount,
                    'naturaleza': 'Descuento'
                    # FIXME   Change it for real discount nature
                }]})
                invoice_totals['totaldescuentos'] += discount
            subtotal = subtotal_before_discount - discount
            exempt_subtotal = subtotal_before_discount
            taxed_subtotal = 0.0
            exonerated_subtotal = 0.0
            tax_amount = tax_returned = 0.0
            exonerated_tax_amount = 0.0
            if line.tax_ids:
                taxes, tax_returned = invoice.get_taxes(line, round(subtotal, 5))

                if taxes:
                    exempt_subtotal = 0.0
                    line_data.update({'impuestos': taxes})
                    tax_amount = sum(item['monto'] for item in taxes)
                    exonerated_tax_amount = sum(
                        tax['exoneracion']['montoexoneracion'] for tax in taxes
                        if 'exoneracion' in tax)
                    if exonerated_tax_amount:
                        exonerated_proportion = \
                            exonerated_tax_amount / (tax_amount or 1)
                        exonerated_subtotal = round(
                            subtotal_before_discount * (exonerated_proportion or 1), 5)
                        taxed_subtotal = \
                            subtotal_before_discount - exonerated_subtotal
                    else:
                        taxed_subtotal = subtotal_before_discount
            line_data.update({
                'subtotal': round(subtotal, 5),
                'impuestoneto': round(tax_amount - exonerated_tax_amount, 5),
                'montototallinea': round(
                    subtotal + tax_amount - exonerated_tax_amount, 5)
            })
            invoice_totals[
                'totalimpuestos'] += tax_amount - exonerated_tax_amount
            invoice_lines.append(line_data)
            if (line.product_id and
                    line.product_id.l10n_cr_edi_uom_id.uom_type == 'service'):
                invoice_totals['totalserviciogravado'] += taxed_subtotal
                invoice_totals['totalservicioexento'] += exempt_subtotal
                invoice_exonerated[
                    'totalservicioexonerado'] += exonerated_subtotal
                invoice_totals['totalivadevuelto'] = tax_returned
            else:
                invoice_totals['totalmercaderiagravado'] += taxed_subtotal
                invoice_totals['totalmercaderiaexento'] += exempt_subtotal
                invoice_exonerated['totalmercaderiaexonerado'] += (
                    exonerated_subtotal)

        invoice_totals['totalserviciogravado'] = round(
            invoice_totals['totalserviciogravado'], 5)
        invoice_totals['totalservicioexento'] = round(
            invoice_totals['totalservicioexento'], 5)
        invoice_exonerated['totalservicioexonerado'] = round(
            invoice_exonerated['totalservicioexonerado'], 5)
        invoice_totals['totalmercaderiagravado'] = round(
            invoice_totals['totalmercaderiagravado'], 5)
        invoice_totals['totalmercaderiaexento'] = round(
            invoice_totals['totalmercaderiaexento'], 5)
        invoice_exonerated['totalmercaderiaexonerado'] = round(
            invoice_exonerated['totalmercaderiaexonerado'], 5)
        invoice_totals['totalivadevuelto'] = round(
            invoice_totals['totalivadevuelto'], 5)

        invoice_totals['totalgravado'] = round(
            invoice_totals['totalserviciogravado'] +
            invoice_totals['totalmercaderiagravado'], 5)
        invoice_totals['totalexento'] = round(
            invoice_totals['totalservicioexento'] +
            invoice_totals['totalmercaderiaexento'], 5)
        invoice_exonerated['totalexonerado'] = round(
            invoice_exonerated['totalservicioexonerado'] +
            invoice_exonerated['totalmercaderiaexonerado'], 5)
        invoice_totals['totalventa'] = round(
            invoice_totals['totalgravado'] + invoice_totals['totalexento'] +
            invoice_exonerated['totalexonerado'], 5)
        invoice_totals['totalventaneta'] = round(
            invoice_totals['totalventa'] -
            invoice_totals['totaldescuentos'], 5)
        invoice_totals['totalcomprobante'] += round(
            invoice_totals['totalventaneta'] +
            invoice_totals['totalimpuestos'] -
            invoice_totals['totalivadevuelto'], 5)
        if invoice_exonerated['totalexonerado']:
            invoice_totals.update(invoice_exonerated)
        if not invoice_totals['totalivadevuelto']:
            del invoice_totals['totalivadevuelto']
        return invoice_totals, invoice_lines, other_charges

    def l10n_cr_edi_is_required(self):
        self.ensure_one()
        return self.company_id.country_id == self.env.ref('base.cr')

    def get_reference_information(self, invoice):
        date = invoice.l10n_cr_edi_reference_datetime
        inv = False
        if self.l10n_cr_edi_ref_doc == '01':
            if invoice.l10n_cr_edi_ref_id:
                inv = invoice.l10n_cr_edi_ref_id
            else:
                inv = invoice.search(
                    [('name', '=', invoice.l10n_cr_edi_ref_num)])
        if inv and inv.id != invoice.id and inv.l10n_cr_edi_emission_datetime:
            date = inv.l10n_cr_edi_emission_datetime
        reference = {
            'tipo_documento': invoice.l10n_cr_edi_ref_doc,
            'numero_documento':
                inv and inv.l10n_cr_edi_full_number or
                invoice.l10n_cr_edi_ref_num,
            'fecha_emision': date and date.strftime(
                "%Y-%m-%dT%H:%M:%S-06:00") or False,
            'codigo': invoice.l10n_cr_edi_ref_type,
            'razon': invoice.l10n_cr_edi_ref_reason
        }
        if (inv and invoice.l10n_cr_edi_ref_type in
                ['01', '02'] and inv.amount_total == invoice.amount_total):
            # Full refund
            reference['codigo'] = '01'
        elif inv and invoice.l10n_cr_edi_ref_type in ['01', '02']:
            # Fix amount
            reference['codigo'] = '02'
            # TODO: Must be a list of references
        return [reference]

    def _l10n_cr_edi_answer_request_xml(self, invoice, payload):
        """ Create the JSON/XML attachment for the invoice passed as parameter.
        :param move:    An account.move record.
        :return:        A dictionary with the structure requested by PAC or an
        error if the cfdi was not successfuly generated.
        """
        response_document = self.l10n_cr_edi_call_service('consultahacienda', {}, json.dumps(payload))
        response_content = json.loads(response_document._content)
        invoice.l10n_cr_edi_return_code = response_content.get('code')

        return True

    def _l10n_cr_edi_export_invoice_xml(self, invoice):
        """ Create the JSON/XML attachment for the invoice passed as parameter.
        :param move:    An account.move record.
        :return:        A dictionary with the structure requested by PAC or an
        error if the cfdi was not successfuly generated.
        """
        # == XML values ==
        xml_values = self._l10n_cr_edi_get_invoice_xml_values(invoice)
        return xml_values

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'fedgt_4_3' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fedgt_4_3':
            return super()._is_compatible_with_journal(journal)
        return journal.type in ['sale', 'purchase'] and journal.country_code == 'CR'

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fedgt_4_3':
            return super()._is_required_for_invoice(invoice)

        # Determine on which invoices the XML must be generated.
        return invoice.move_type in (
            'out_invoice', 'out_refund', 'in_invoice', 'in_refund') and invoice.country_code == 'CR'

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        edi_result = super()._post_invoice_edi(invoices, test_mode=test_mode)
        if self.code != 'fedgt_4_3':
            return edi_result

        for invoice in invoices:
            # == Check the configuration ==
            errors = self._l10n_cr_edi_check_configuration(invoice)
            if errors:
                edi_result[invoice] = {
                    'error': self._l10n_cr_edi_format_error_message(_("Invalid configuration:"), errors),
                }
                continue

            # == Generate the XML==
            res = self._l10n_cr_edi_export_invoice_xml(invoice)
            if res.get('errors'):
                edi_result[invoice] = {
                    'error': self._l10n_cr_edi_format_error_message(
                        _("Failure during the generation of the XML:"), res['errors']),
                }

            # == Call the web-service ==
            response_document = invoice.l10n_cr_edi_call_service(
                'makeXML', {}, json.dumps(res)
            )
            response_content = json.loads(response_document._content)

            if response_document.status_code != 200 or \
                    response_content.get('code') not in [1, 43, 44]:
                invoice.write({
                    'l10n_cr_edi_sat_status': 'not_signed',
                    'l10n_cr_edi_return_code': response_content.get('code'),
                })
                attach_xml_file = base64.b64encode(json.dumps(res).encode())
                error = response_content.get('error') or response_content.get('xml_error')
                error_message = "%s: %s" % (response_content.get('code'), error)
                edi_result[invoice] = {
                    'error': self._l10n_cr_edi_format_error_message(
                        _("Failure during the generation of the XML:"), [error_message]),
                }
                continue

            if response_content.get('clave'):
                number = response_content.get('clave')
                invoice.write({
                    'name': number[21:41],
                    'l10n_cr_edi_type': res['clave']['tipo'],
                    'l10n_cr_edi_full_number': number,
                    'l10n_cr_edi_sat_status': 'signed',
                    'l10n_cr_edi_return_code': response_content.get('code'),
                })

            # == Create the attachments ==
            attach_xml_file = response_content.get('data')
            fedgt_attachment = self._create_fedgt_attachment(invoice, attach_xml_file)
            edi_result[invoice] = {'attachment': fedgt_attachment}

            # == Chatter ==
            invoice.with_context(no_new_invoice=True).message_post(
                body=_("The XML document was successfully created and signed by the government."),
                attachment_ids=fedgt_attachment.ids,
            )
            invoice.electronic_answer_request()
            if invoice.l10n_cr_edi_sat_status != 'signed':
                invoice.l10n_cr_edi_send_mail()
        return edi_result

    def _create_fedgt_attachment(self, invoice, data):
        document_types = {
            '01': _('FE-%s.xml'),
            '02': _('ND-%s.xml'),
            '04': _('TE-%s.xml'),
            '08': _('FEC-%s.xml'),
            '09': _('FEE-%s.xml')
        }
        if invoice.move_type in ['out_refund', 'in_refund']:
            xml_filename = _('NC-%s.xml') % invoice.name
        if invoice.journal_id.l10n_cr_edi_document_type in document_types:
            xml_filename = document_types[
                invoice.journal_id.l10n_cr_edi_document_type] % invoice.name
        return self.env['ir.attachment'].create({
            'name': xml_filename,
            'res_id': invoice.id,
            'res_model': invoice._name,
            'type': 'binary',
            'datas': data,
            'mimetype': 'application/xml',
            'description': _('Electronic invoice generated for the %s document.') % invoice.name,
        })

    def _cancel_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        edi_result = super()._cancel_invoice_edi(invoices, test_mode=test_mode)
        return edi_result
