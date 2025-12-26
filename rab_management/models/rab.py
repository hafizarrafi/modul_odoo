from odoo import models, fields, api


class RabManagement(models.Model):
    _name = 'rab.management'
    _description = 'RAB Management'
    _order = 'id desc'

    name = fields.Char(
        string='RAB Number',
        required=True,
        copy=False,
        default='New'
    )

    date = fields.Date(
        default=fields.Date.today
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], default='draft')

    line_ids = fields.One2many(
        'rab.management.line',
        'rab_id',
        string='RAB Lines'
    )

    total_amount = fields.Monetary(
        compute='_compute_total',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rab.management'
                ) or 'New'
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.name == 'New' and vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rab.management'
                ) or 'New'
        return super().write(vals)
