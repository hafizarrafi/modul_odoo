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
            'views/rab_owl_actions.xml',
            'views/partner_view.xml',
            'views/rab_view.xml',
            'views/menu.xml',
            'views/rab_vendor_comparison.xml',
            'views/rab_vendor_comparison_pivot.xml',
    ],
    'application': True,
    'license': 'LGPL-3',

    'assets': {
        'web.assets_backend': [
            'rab_management/static/src/owl/actions/rab_vendor_comparison.js',
            'rab_management/static/src/owl/components/vendor_matrix/vendor_matrix.js',
            'rab_management/static/src/owl/xml/rab_vendor_comparison.xml',
            'rab_management/static/src/owl/components/vendor_matrix/vendor_matrix.xml',
            'rab_management/static/src/scss/rab_vendor_comparison.scss',
        ],
    },



    


    

}
