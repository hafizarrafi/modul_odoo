{
    'name': 'RAB Management',
    'version': '1.0',
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
            'views/partner_view.xml',
            'views/rab_view.xml',
            'views/menu.xml',
            'views/rab_vendor_comparison.xml',
            'views/rab_vendor_comparison_pivot.xml',
    ],
    'application': True,
    'license': 'LGPL-3',

    


    

}
