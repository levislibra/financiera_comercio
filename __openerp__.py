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
    'depends': ['financiera_prestamos', 'mail'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
        'data/ir_cron.xml',
        'views/reports.xml',
        'financiera_comercio_report.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}