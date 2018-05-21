# -*- coding: utf-8 -*-
{
    'name': "Financiera Comercio",

    'summary': """
        Gestion de credito en comercios.""",

    'description': """
        Gestion de credito en comercios.
    """,

    'author': "Librasoft",
    'website': "http://www.libra-soft.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'financial',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['financiera_base', 'financiera_prestamos'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}