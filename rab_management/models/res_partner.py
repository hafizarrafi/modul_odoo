from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_type = fields.Selection(
        [
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
            ('both', 'Both'),
        ],
        string='Contact Type',
        required=True,
        default='customer',
    )

    @api.onchange('contact_type')
    def _onchange_contact_type(self):
        for partner in self:
            if partner.contact_type in ('customer', 'both'):
                partner.customer_rank = 1
            else:
                partner.customer_rank = 0

            if partner.contact_type in ('supplier', 'both'):
                partner.supplier_rank = 1
            else:
                partner.supplier_rank = 0
