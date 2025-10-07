import datetime

from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, PYSONEncoder, Date
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, Button

from .library import QUARANTINE_ZONE_DURATION

__all__ = [
    'PutInBookshelf',
    'PutInBookshelfParameters',
    'PutInStorageBookshelf',
    'PutInStorageBookshelfParameters',
    'Reserve',
    'ReserveSelectBooks',
    'CreateExemplaries',
    'CreateExemplariesParameters'
    'Borrow',
    'Return'
    ]


class PutInBookshelf(Wizard):
    'Put In Bookshelf'

    __name__ = 'library.book.exemplary.put_in_bookshelf'

    start_state = 'check_eligibility'
    check_eligibility = StateTransition()
    parameters = StateView('library.book.exemplary.put_in_bookshelf.parameters',
    'library_location.put_in_bookshelf_parameters_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Put', 'put', 'tryton-go-next',
            default=True)])
    put = StateTransition()

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'ineligible': 'Some selected exemplaries are either in quarantine or currenty chcked out '
                'and therefore cannot be moved to the selected bookshelf :\n- %(exemplaries)s',
                'not_enough_space_in_bookshelf': 'There is not enough space in the bookshelf to put'
                'the selected exemplaries'})
        
    def default_parameters(self, name):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))

        return {
            'exemplaries': [e.id for e in exemplaries if not (e.is_in_quarantine or e.is_checked_out)]
        }
    
    
    def transition_check_eligibility(self):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))
        
        ineligible = [e.rec_name for e in exemplaries if (e.is_in_quarantine or e.is_checked_out)]

        if ineligible:
            self.raise_user_warning(
                ', '.join(ineligible),
                'ineligible',
                {
                    'exemplaries' : '\n- '.join(ineligible)
                }
            )

        return 'parameters'
    
    def transition_put(self):
        nb_exemplaries_to_put = len(self.parameters.exemplaries)
        
        if nb_exemplaries_to_put > self.parameters.target_bookshelf.available_slots:
            self.raise_user_error('not_enough_space_in_bookshelf')
        
        Exemplary = Pool().get('library.book.exemplary')
        Exemplary.write(list(self.parameters.exemplaries), {
                'bookshelf': self.parameters.target_bookshelf})
        
        return 'end'


class PutInBookshelfParameters(ModelView):
    'Put In bookshelf Parameters'

    __name__ = 'library.book.exemplary.put_in_bookshelf.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True,
        depends = ['is_in_quarantine', 'is_checked_out'],
        domain = [('is_in_quarantine' ,'=', False), ('is_checked_out', '=', False)])
    target_bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Target Bookshelf',
                                       required=True,
                                       domain=[('is_full', '=', False)])
    

class PutInStorage(Wizard):
    'Put In Storage'

    __name__ = 'library.book.exemplary.put_in_storage'

    start_state = 'check_eligibility'
    check_eligibility = StateTransition()
    parameters = StateView(
        'library.book.exemplary.put_in_storage.parameters',
        'library_location.exemplary_put_in_storage_view_form', [
        Button('Cancel', 'end', 'tryton-cancel'),
        Button('Put in storage', 'put_in', 'tryton-go-next',
            default=True)]
    )
    put_in = StateTransition()

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'ineligible': 'Some selected exemplaries are not available or already in storage'
                'and therefore cannot be moved to storage :\n- %(exemplaries)s'
                })

    def default_parameters(self, name):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))

        return {
            'exemplaries': [e.id for e in exemplaries if e.is_available]
        }
    
    def transition_check_eligibility(self):
        Exemplary = Pool().get('library.book.exemplary')
        exemplaries = Exemplary.browse(
                Transaction().context.get('active_ids'))
        
        ineligible = [e.rec_name for e in exemplaries if not e.is_available]

        if ineligible:
            self.raise_user_warning(
                ', '.join(ineligible),
                'ineligible',
                {
                    'exemplaries' : '\n- '.join(ineligible)
                }
            )

        return 'parameters'

    def transition_put_in(self):
        Exemplary = Pool().get('library.book.exemplary')

        Exemplary.write(list(self.parameters.exemplaries), {
                'bookshelf': None})
        
        return 'end'


class PutInStorageParameters(ModelView):
    'Take Ouf Of Bookshelf Parameters'

    __name__ = 'library.book.exemplary.put_in_storage.parameters'

    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True,
        domain = [('is_available', "=", True)],
        depends = ['is_available'])


class Reserve(Wizard):
    'Reserve books'
    __name__ = 'library.user.reserve'

    start_state = 'select_books'
    select_books = StateView('library.user.reserve.select_books',
        'library_location.reserve_select_books_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Reserve', 'reserve', 'tryton-go-next', default=True)])
    reserve = StateTransition()
    checkouts = StateAction('library_borrow.act_open_user_checkout')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._error_messages.update({
                'available': 'Exemplary %(exemplary)s is currently available,'
                'it should be borrowed instead of reserved',
                'still_in_quarantine': 'Quarantine for exemplary %(exemplary)s is ending '
                '%(end_of_quarantine)s at the selected reservation date.',
                'still_in_quarantine_after_current_checkout': 'Exemplary %(exemplary)s is currently ' 
                'checked out until %(end_of_checkout)s and will then be in quarantine until '
                '%(end_of_quarantine)s',
                'already_reserved': 'Exemplary %(exemplary)s is already_reserved'
                })

    def default_select_books(self, name):
        return {
            'user': Transaction().context.get('active_id')
            }
    
    def transition_reserve(self):
        pool = Pool()
        Checkout = pool.get('library.user.checkout')
        Quarantine_Zone = pool.get('library.quarantine_zone')
        exemplaries = self.select_books.exemplaries
        user = self.select_books.user
        checkouts = []
        for exemplary in exemplaries:
            if exemplary.is_reserved:
                self.raise_user_error('already_reserved', {
                        'exemplary': exemplary.rec_name})
                
            if exemplary.is_available:
                self.raise_user_error('available', {
                        'exemplary': exemplary.rec_name})
                
            if exemplary.is_in_quarantine:
                quarantine_zone = Quarantine_Zone.search([('exemplary', '=', exemplary),
                                                          ('end_date', '>', datetime.date.today())])
                quarantine_end_date = quarantine_zone[0].end_date
                if self.select_books.date < quarantine_end_date:
                    self.raise_user_error('still_in_quarantine', {
                        'exemplary': exemplary.rec_name,
                        'quarantine_end_date': quarantine_end_date}) 
                    
            if exemplary.is_checked_out:
                current_checkout = Checkout.search([('exemplary', '=', exemplary),
                                            ('return_date', '=', None),
                                            ('date', '<=', datetime.date.today())])
                min_reserve_date = current_checkout[0].expected_return_date + datetime.timedelta(QUARANTINE_ZONE_DURATION)
                if self.select_books.date < min_reserve_date:
                    self.raise_user_error('still_in_quarantine_after_current_checkout', {
                        'exemplary': exemplary.rec_name,
                        'end_of_checkout': current_checkout[0].expected_return_date,
                        'end_of_quarantine': min_reserve_date}) 

            checkouts.append(Checkout(
                    user=user, date=self.select_books.date,
                    exemplary=exemplary))
        Checkout.save(checkouts)
        self.select_books.checkouts = checkouts
        return 'checkouts'
    
    def do_checkouts(self, action):
        action['pyson_domain'] = PYSONEncoder().encode([
                ('id', 'in', [x.id for x in self.select_books.checkouts])])
        return action, {}
    

class ReserveSelectBooks(ModelView):
    'Select Books'
    __name__ = 'library.user.reserve.select_books'

    user = fields.Many2One('library.user', 'User', required=True)
    exemplaries = fields.Many2Many('library.book.exemplary', None, None,
        'Exemplaries', required=True, domain=[('is_available', '=', False),
                                              ('is_in_storage', '=', False),
                                              ('is_reserved', '=', False)])
    date = fields.Date('Date', required=True, domain=[('date', '>', Date())])
    checkouts = fields.Many2Many('library.user.checkout', None, None,
        'Checkouts', readonly=True)
        

class CreateExemplaries(metaclass=PoolMeta):
    'Create Exemplaries'
    __name__ = 'library.book.create_exemplaries'
    
    def transition_create_exemplaries(self):
        res = super().transition_create_exemplaries()

        Exemplary = Pool().get('library.book.exemplary')

        created_exemplaries = self.parameters.exemplaries
        to_bookshelf = created_exemplaries[self.parameters.nb_to_put_in_storage:]

        Exemplary.write(list(to_bookshelf), {'bookshelf': self.parameters.target_bookshelf.id})

        return res
        

class CreateExemplariesParameters(metaclass=PoolMeta):
    __name__ = 'library.book.create_exemplaries.parameters'

    target_bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Target Bookshelf',
                                       help='The bookshelf the exemplaries will be stored in',
                                       required=True)
    
    nb_to_put_in_storage = fields.Integer('Nb to put in storage', help='Number of exemplaries to put in storage',
                                          required=True,
                                          depends=['number_of_exemplaries'],
                                          domain=[('nb_to_put_in_storage', '>=', 0),
                                                  ('nb_to_put_in_storage', '<=', Eval('number_of_exemplaries'))])


class Borrow(metaclass=PoolMeta):
    __name__ = 'library.user.borrow'

    def transition_borrow(self):
        res = super().transition_borrow()

        Exemplary = Pool().get('library.book.exemplary')
        Exemplary.write(list(self.select_books.exemplaries), {'bookshelf': None})

        return res


class Return(metaclass=PoolMeta):
    __name__ = 'library.user.return'

    def transition_return_(self):
        res = super().transition_return_()
        pool = Pool()
        QuarantineZone = pool.get('library.quarantine_zone')
        Exemplary = pool.get('library.book.exemplary')
        Checkout = pool.get('library.user.checkout')
        to_create = []

        for checkout in self.select_checkouts.checkouts:
            quarantine_zone = QuarantineZone()
            quarantine_zone.exemplary = checkout.exemplary.id
            quarantine_zone.start_date = self.select_checkouts.date
            to_create.append(quarantine_zone)

            if checkout.return_date < checkout.expected_return_date and checkout.exemplary.is_reserved:
                reservation_checkout_id = Exemplary.get_checkout_reserve_id(checkout.exemplary.id)[0]
                Checkout.write(Checkout.browse([reservation_checkout_id]), {
                    'date': checkout.return_date + datetime.timedelta(QUARANTINE_ZONE_DURATION)
                })
    
        QuarantineZone.save(to_create)

        return res