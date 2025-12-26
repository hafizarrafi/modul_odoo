from odoo import models, fields, api


class RabManagement(models.Model):
    _name = 'rab.management'
    _description = 'RAB Management'

    name = fields.Char(
        string="RAB Number",
        required=True,
        default=lambda self: 'New'
    )

    date = fields.Date(
        string="RAB Date",
        default=fields.Date.today
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
    ], default='draft')

    line_ids = fields.One2many(
        'rab.management.line',
        'rab_id',
        string="RAB Lines"
    )
