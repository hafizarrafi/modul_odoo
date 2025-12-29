from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    contact_type = fields.Selection(
        [
            ('supplier', 'Supplier'),
            ('customer', 'Customer'),
            ('both', 'Both'),
        ],
        compute='_compute_contact_type',
        store=True,
    )

    @api.depends('customer_rank', 'supplier_rank')
    def _compute_contact_type(self):
        for partner in self:
            if partner.customer_rank > 0 and partner.supplier_rank > 0:
                partner.contact_type = 'both'
            elif partner.customer_rank > 0:
                partner.contact_type = 'customer'
            elif partner.supplier_rank > 0:
                partner.contact_type = 'supplier'
            else:
                partner.contact_type = False
