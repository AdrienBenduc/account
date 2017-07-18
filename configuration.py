# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond import backend
from trytond.pool import Pool
from trytond.model import ModelView, ModelSQL, ModelSingleton, fields
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)
from trytond.tools.multivalue import migrate_property

__all__ = ['Configuration', 'ConfigurationDefaultAccount',
    'ConfigurationTaxRounding']
tax_roundings = [
    ('document', 'Per Document'),
    ('line', 'Per Line'),
    ]


class Configuration(
        ModelSingleton, ModelSQL, ModelView, CompanyMultiValueMixin):
    'Account Configuration'
    __name__ = 'account.configuration'
    default_account_receivable = fields.MultiValue(fields.Many2One(
            'account.account', "Default Account Receivable",
            domain=[
                ('kind', '=', 'receivable'),
                ('company', '=', Eval('context', {}).get('company', -1)),
                ]))
    default_account_payable = fields.MultiValue(fields.Many2One(
            'account.account', "Default Account Payable",
            domain=[
                ('kind', '=', 'payable'),
                ('company', '=', Eval('context', {}).get('company', -1)),
                ]))
    tax_rounding = fields.MultiValue(fields.Selection(
            tax_roundings, "Tax Rounding"))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'default_account_receivable', 'default_account_payable'}:
            return pool.get('account.configuration.default_account')
        return super(Configuration, cls).multivalue_model(field)

    @classmethod
    def default_tax_rounding(cls, **pattern):
        return cls.multivalue_model('tax_rounding').default_tax_rounding()


class ConfigurationDefaultAccount(ModelSQL, CompanyValueMixin):
    "Account Configuration Default Account"
    __name__ = 'account.configuration.default_account'

    configuration = fields.Many2One('account.configuration', 'Configuration',
        ondelete='CASCADE', select=True)
    default_account_receivable = fields.Many2One(
        'account.account', "Default Account Receivable",
        domain=[
            ('kind', '=', 'receivable'),
            ('company', '=', Eval('company', -1)),
            ],
        depends=['company'])
    default_account_payable = fields.Many2One(
        'account.account', "Default Account Payable",
        domain=[
            ('kind', '=', 'payable'),
            ('company', '=', Eval('company', -1)),
            ],
        depends=['company'])

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        exist = TableHandler.table_exist(cls._table)
        super(ConfigurationDefaultAccount, cls).__register__(module_name)
        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.extend(['account_receivable',
                'account_payable'])
        value_names.extend(['default_account_receivable',
                'default_account_payable'])
        fields.append('company')
        migrate_property(
            'party.party', field_names, cls, value_names,
            fields=fields)


class ConfigurationTaxRounding(ModelSQL, CompanyValueMixin):
    'Account Configuration Tax Rounding'
    __name__ = 'account.configuration.tax_rounding'
    configuration = fields.Many2One('account.configuration', 'Configuration',
        required=True, ondelete='CASCADE')
    tax_rounding = fields.Selection(tax_roundings, 'Method', required=True)

    @classmethod
    def __register__(cls, module_name):
        TableHandler = backend.get('TableHandler')
        sql_table = cls.__table__()
        cursor = Transaction().connection.cursor()

        exist = TableHandler.table_exist(cls._table)
        super(ConfigurationTaxRounding, cls).__register__(module_name)

        table = TableHandler(cls, module_name)

        # Migration from 4.2: rename method into tax_rounding
        if table.column_exist('method'):
            cursor.execute(*sql_table.update(
                    [sql_table.tax_rounding], [sql_table.method]))
            table.drop_column('method')
        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('tax_rounding')
        value_names.append('tax_rounding')
        fields.append('company')
        migrate_property(
            'account.configuration', field_names, cls, value_names,
            parent='configuration', fields=fields)

    @classmethod
    def default_tax_rounding(cls):
        return 'document'
