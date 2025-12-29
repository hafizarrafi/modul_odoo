{
    'name': 'RAB Management',
    'version': '1.3.1',
    'category': 'Accounting',
    'summary': 'Budget Plan (RAB) Management',
    'author': 'YourCompany',
    'depends': [
        'base',
        'product',
        'contacts',
        'sale',       
        'purchase',   
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/rab_view.xml',
        'views/menu.xml',
        'views/rab_vendor_comparison.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}
