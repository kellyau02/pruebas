from odoo import http
from odoo.http import request
import logging
import werkzeug

_logger = logging.getLogger(__name__)

class TilopayController(http.Controller):
    _tilopay_view_url = '/payment/tilopay/view'
    _confirmation_url = 'payment/paypal/confirmation'
    _response_url = '/payment/tilopay/response'
    _return_url = 'payment/paypal/confirmation'
    _notify_url = '/payment/tilopay/notify'
    
    @http.route('/payment/tilopay/view', type='http', auth='public', csrf=False)
    def tilopay_view(self, **post):        
        _logger.info('*** tilopay_view ***')
        return werkzeug.utils.redirect(post["url_payment"])

    @http.route([
        '/payment/paypal/confirmation',
    ], type='http', auth='public', csrf=False)
    def tilopay_confirmation(self, **post):
        _logger.info('*** tilopay_confirmation ***')
        if post:
            request.env["payment.transaction"].sudo().form_feedback(post, 'tilopay')
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/tilopay/response', type='http', auth='public', csrf=False)
    def tilopay_response(self, **post):
        _logger.info("*** tilopay_response ***")
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'tilopay')
        return werkzeug.utils.redirect('/payment/process')
    
    @http.route([
        '/payment/tilopay/return',
    ], type='http', auth='public', csrf=False)
    def tilopay_return(self, **post):
        _logger.info('*** tilopay_return ***')
        return werkzeug.utils.redirect('/payment/process')

    @http.route([
        '/payment/tilopay/notify',
    ], type='http', auth='public', methods=['POST'], csrf=False)
    def tilopay_notify(self, **post):
        _logger.info('*** tilopay_notify ***')
        return '[accepted]'