{
    'name': 'RAB Management',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Budget Plan (RAB) Management',
    'depends': ['base'],

   'data': [
    'security/ir.model.access.csv',
    'data/ir_sequence_data.xml',
    'views/views.xml',   # ACTION & VIEW DULU
    'views/menu.xml',    # MENU TERAKHIR
    ],


    'application': True,
    'license': 'LGPL-3',
}
