import datetime

from sql import Literal, Null
from sql.conditionals import Coalesce
from sql.aggregate import Count
from sql.operators import Equal, NotEqual, Greater, GreaterEqual, Less, LessEqual, In, NotIn

from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import ModelSQL, ModelView, fields
from trytond.pyson import Date


__all__ = [
    'Floor',
    'Room',
    'Bookshelf',
    'Exemplary',
    'Book',
    'Checkout',
    'QuarantineZone'
    ]

QUARANTINE_ZONE_DURATION=7


class MixinExemplaryState():
    @classmethod
    def get_sql_where_exemplary_is_in_quarantine(cls, quarantine_zone):
        return ((quarantine_zone.start_date > (datetime.date.today() - datetime.timedelta(days=7))) 
                & (quarantine_zone.id != Null))
    
    @classmethod
    def get_sql_where_exemplary_is_checked_out(cls, checkout):
        return ((checkout.return_date == Null)
                & (checkout.id != Null)
                & (checkout.date <= datetime.date.today()))
    
    @classmethod
    def get_sql_where_exemplary_is_in_bookshelf(cls, exemplary, is_in=True):
        return (exemplary.bookshelf != Null) if is_in else (exemplary.bookshelf == Null)
    
    @classmethod
    def get_sql_query_for_field_getter(cls, in_bookshelf, id_filter=None):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = pool.get('library.book.exemplary').__table__()
        quarantine_zone = pool.get('library.quarantine_zone').__table__()
    
        where = (cls.get_sql_where_exemplary_is_checked_out(checkout) |
                cls.get_sql_where_exemplary_is_in_quarantine(quarantine_zone) |
                cls.get_sql_where_exemplary_is_in_bookshelf(exemplary, is_in=in_bookshelf)
                )
            
        if id_filter:
            where &= exemplary.id.in_(id_filter)

        return exemplary.join(
                checkout,
                'LEFT OUTER',
                condition=(checkout.exemplary == exemplary.id)
            ).join(
                quarantine_zone,
                'LEFT OUTER',
                condition=(quarantine_zone.exemplary == exemplary.id)
            ).select(exemplary.id, where=where)
    
    @staticmethod
    def get_checkout_reserve_id(exemplary_id):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        cursor = Transaction().connection.cursor()
        query = checkout.select(
            checkout.id,
            where=(
                    (checkout.return_date == Null) &
                    (checkout.date > datetime.date.today()) &
                    (checkout.exemplary == exemplary_id)
                    )
            )

        cursor.execute(*query)
        
        return cursor.fetchone()


class Floor(ModelSQL, ModelView):
    'Floor'

    __name__ = 'library.floor'

    name = fields.Char('Name', required=True)
    rooms = fields.One2Many('library.floor.room', 'floor', 'Rooms')
    number_of_rooms = fields.Function(
        fields.Integer('Number of rooms', help='The number of rooms of this floor'),
        'getter_number_of_rooms'
    )

    @classmethod
    def getter_number_of_rooms(cls, floors, name):
        room = Pool().get('library.floor.room').__table__()
        cursor = Transaction().connection.cursor()

        cursor.execute(*room.select(room.floor, Count(room.floor),
                where=room.floor.in_([f.id for f in floors]),
                group_by=[room.floor]))
        
        return dict(cursor.fetchall())
    

class Room(ModelSQL, ModelView):
    'Room'

    __name__ = 'library.floor.room'

    name = fields.Char('Name', required=True)
    floor = fields.Many2One('library.floor', 'Floor', required=True,
        ondelete='CASCADE', select=True)
    bookshelves = fields.One2Many('library.floor.room.bookshelf', 'room', 'Bookshelves')
    number_of_bookshelves = fields.Function(
        fields.Integer('Number of bookshelves', help='The number of bookshelves in this room'),
        'getter_number_of_bookshelves'
    )

    @classmethod
    def getter_number_of_bookshelves(cls, rooms, name):
        bookshelf = Pool().get('library.floor.room.bookshelf').__table__()
        cursor = Transaction().connection.cursor()

        cursor.execute(*bookshelf.select(bookshelf.room, Count(bookshelf.room),
                where=bookshelf.room.in_([r.id for r in rooms]),
                group_by=[bookshelf.room]))
        
        return dict(cursor.fetchall())
    

class Bookshelf(ModelSQL, ModelView):
    'Bookshelf'

    __name__ = 'library.floor.room.bookshelf'

    name = fields.Char('Name', required=True)
    room = fields.Many2One('library.floor.room', 'Room', required=True,
        ondelete='CASCADE', select=True)
    exemplaries = fields.One2Many('library.book.exemplary', 'bookshelf', 'Exemplaries',
                                  readonly=True)
    capacity = fields.Integer('Capacity', help='The maximum number of exemplaries this bookshelf'
                'can contain', required=True)
    number_of_exemplaries= fields.Function(
        fields.Integer('Number of exemplaries', help='The number of exemplaries in this bookshelf'),
        'getter_exemplaries_in_bookshelf',
    )
    available_slots = fields.Function(
        fields.Integer('Available slots', help='The number of available slots in the bookshelf'),
        'getter_exemplaries_in_bookshelf',
        searcher='search_available_slots'
    )
    is_full = fields.Function(
        fields.Boolean('Is full', help='True if the bookshelf is full and' \
        'cannot contain any additional exemplary'),
        'getter_exemplaries_in_bookshelf',
        searcher='search_is_full'
    )

    @classmethod
    def getter_exemplaries_in_bookshelf(cls, bookshelves, name):
        exemplary = Pool().get('library.book.exemplary').__table__()
        bookshelf = cls.__table__()
        default_value = False if name == 'is_full' else 0
        result = {b.id: default_value for b in bookshelves}

        cursor = Transaction().connection.cursor()

        base_query = exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf).as_('count'),
                where=exemplary.bookshelf.in_([b.id for b in bookshelves]),
                group_by=[exemplary.bookshelf])
        
        if name == 'number_of_exemplaries':
            query = base_query
        elif name == 'available_slots':
            query = bookshelf.join(
                base_query,
                'LEFT OUTER',
                condition=(
                    bookshelf.id == base_query.bookshelf
                )).select(bookshelf.id, (bookshelf.capacity - Coalesce(base_query.count, Literal(0))))
        else:
            query = bookshelf.join(
                base_query,
                condition=(
                    bookshelf.id == base_query.bookshelf
                )).select(bookshelf.id, (base_query.count == bookshelf.capacity))
        
        cursor.execute(*query)

        for bookshelf_id, value in cursor.fetchall():
            result[bookshelf_id] = value

        return result
    
    @classmethod
    def search_is_full(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        exemplary = Pool().get('library.book.exemplary').__table__()
        bookshelf = cls.__table__()

        subquery = exemplary.select(exemplary.bookshelf, Count(exemplary.bookshelf).as_('count'),
                group_by=[exemplary.bookshelf])
        
        query = bookshelf.join(subquery, condition=(
            bookshelf.id == subquery.bookshelf
        )).select(bookshelf.id, where=(subquery.count == bookshelf.capacity)
                  )

        return [('id', 'in' if value else 'not in', query)]
    
    @classmethod
    def search_available_slots(cls, name, clause):
        import logging
        logger = logging.info('TEST')
        logger.info("\n"*20)
        logger.info(clause)
        _, operator, value = clause
        exemplary = Pool().get('library.book.exemplary').__table__()
        bookshelf = cls.__table__()

        map = {
            '>': Greater,
            '>=': GreaterEqual,
            '<': Less,
            '<=': LessEqual,
            '=': Equal,
            '!=': NotEqual,
            'in': In,
            'not in': NotIn
        }

        query = bookshelf.join(exemplary,
                               condition=exemplary.bookshelf == bookshelf.id).select(
                                    bookshelf.id,
                                    group_by=[bookshelf.id],
                                    having=map[operator](Count(bookshelf.id), value)
                                )
        logger.info(query)
        return [('id', 'in' , query)]
    
    
class QuarantineZone(ModelSQL, ModelView):
    'Quarantine Zone'

    __name__ = 'library.quarantine_zone'

    exemplary = fields.Many2One('library.book.exemplary', 'Exemplary',
                                help='Exemplary being in quarantine zone',
                                required=True,
                                readonly=True)
    start_date = fields.Date('Start Date', help='Beginning of quarantine',
                             domain=[('start_date', '>=', Date())],
                             required=True,
                             readonly=True)
    end_date = fields.Function(
        fields.Date('End Date', help='End of quarantine'),
        'getter_end_date',
        searcher='search_end_date')
    
    def getter_end_date(self, name):
        return self.start_date + datetime.timedelta(days=7)
    
    @classmethod
    def search_end_date(cls, name, clause):
        _, operator, value = clause

        if isinstance(value, datetime.date):
            value = value - datetime.timedelta(days=QUARANTINE_ZONE_DURATION)
        elif isinstance(value, (list, tuple)):
            value = [(x - datetime.timedelta(days=QUARANTINE_ZONE_DURATION) if x else x) for x in value]

        return [('start_date', operator, value)]
    

class Book(MixinExemplaryState, metaclass=PoolMeta):
    __name__ = 'library.book'

    @classmethod
    def get_query_getter_is_available(cls):
        pool = Pool()
        exemplary = pool.get('library.book.exemplary').__table__()
        book = cls.__table__()
        subquery = cls.get_sql_query_for_field_getter(in_bookshelf=False)
        query = exemplary.join(
                book,
                condition=(exemplary.book == book.id)
            ).select(
                book.id,
                distinct=True,
                where=~exemplary.id.in_(subquery)
            )
        return query


class Exemplary(MixinExemplaryState, metaclass=PoolMeta):
    __name__ = 'library.book.exemplary'

    bookshelf = fields.Many2One('library.floor.room.bookshelf', 'Bookshelf',
        ondelete='RESTRICT', select=True, readonly=True)
    
    # several booleans to define the state of an examplary (being borrowed, in storage, in quarantine...)
    is_in_storage = fields.Function(
        fields.Boolean('Is in storage', help='Boolean to true if the exemplary is currently in storage'),
        'getter_is_in_storage',
        searcher='search_is_in_storage'
    )
    is_in_quarantine = fields.Function(
        fields.Boolean('Is in quarantine', help='Boolean to true if the exemplary is currently in quarantine'),
        'getter_is_in_quarantine',
        searcher='search_is_in_quarantine'
    )
    is_checked_out= fields.Function(
        fields.Boolean('Is checked out', help='Boolean to true if the exemplary is currently checked out'),
        'getter_is_checked_out',
        searcher='search_is_checked_out'
    )
    is_reserved= fields.Function(
        fields.Boolean('Is reserved', help='Boolean to true if the exemplary is reserved'),
        'getter_is_reserved',
        searcher='search_is_reserved'
    )

    @classmethod
    def getter_is_in_storage(cls, exemplaries, name):
        result = {e.id: True for e in exemplaries}
        cursor = Transaction().connection.cursor()
        query = cls.get_sql_query_for_field_getter(in_bookshelf=True,
                                                    id_filter=[x.id for x in exemplaries])
        cursor.execute(*query)
        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = False

        return result
    
    @classmethod
    def getter_is_in_quarantine(cls, exemplaries, name):
        quarantine_zone = Pool().get('library.quarantine_zone').__table__()
        result = {e.id: False for e in exemplaries}
        cursor = Transaction().connection.cursor()

        cursor.execute(*quarantine_zone.select(
            quarantine_zone.exemplary,
            where=(quarantine_zone.exemplary.in_([e.id for e in exemplaries])
                   & cls.get_sql_where_exemplary_is_in_quarantine(quarantine_zone))
            
        ))

        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True

        return result
    
    @classmethod
    def getter_is_checked_out(cls, exemplaries, name):
        result = {e.id: False for e in exemplaries}
        checkout = Pool().get('library.user.checkout').__table__()
        cursor = Transaction().connection.cursor()
        cursor.execute(*checkout.select(checkout.exemplary,
                where=cls.get_sql_where_exemplary_is_checked_out(checkout)
                & checkout.exemplary.in_([x.id for x in exemplaries])))

        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True
        return result
    
    @classmethod
    def getter_is_reserved(cls, exemplaries, name):
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        result = {e.id: False for e in exemplaries}
        cursor = Transaction().connection.cursor()
        cursor.execute(*exemplary.join(
            checkout, 'LEFT OUTER',
            condition=(exemplary.id == checkout.exemplary)
        ).select(
            exemplary.id,
            where=(
                    (checkout.return_date == Null) &
                    (checkout.id != Null) &
                    (checkout.date > datetime.date.today()) &
                    checkout.exemplary.in_([e.id for e in exemplaries])
                )
            )
        )

        for exemplary_id, in cursor.fetchall():
            result[exemplary_id] = True
        return result
    
    @classmethod
    def search_is_in_storage(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value       
                
        query = cls.get_sql_query_for_field_getter(in_bookshelf=True)
        
        return [('id', 'not in' if value else 'in', query)]
    
    @classmethod
    def search_is_in_quarantine(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        quarantine_zone = Pool().get('library.quarantine_zone').__table__()

        query = quarantine_zone.select(
            quarantine_zone.exemplary,
            where=cls.get_sql_where_exemplary_is_in_quarantine(quarantine_zone))
            
        return [('id', 'in' if value else 'not in', query)]
    
    @classmethod
    def search_is_checked_out(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value
        
        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()

        query = checkout.select(checkout.exemplary,
                where=cls.get_sql_where_exemplary_is_checked_out(checkout))

        return [('id', 'in' if value else 'not in', query)]
    
    @classmethod
    def search_is_reserved(cls, name, clause):
        _, operator, value = clause
        if operator == '!=':
            value = not value

        pool = Pool()
        checkout = pool.get('library.user.checkout').__table__()
        exemplary = cls.__table__()
        query = exemplary.join(
            checkout, 'LEFT OUTER', 
            condition=(exemplary.id == checkout.exemplary)
        ).select(
            exemplary.id,
            where=(
                    (checkout.return_date == Null) &
                    (checkout.id != Null) &
                    (checkout.date > datetime.date.today())
                )
            )
        return [('id', 'in' if value else 'not in', query)]
    
    @classmethod
    def get_query_getter_is_available(cls, exemplaries):
        return cls.get_sql_query_for_field_getter(in_bookshelf=False,
                                                    id_filter=[x.id for x in exemplaries])
    
    @classmethod
    def get_query_search_is_available(cls):
        return cls.get_sql_query_for_field_getter(in_bookshelf=False)
    
    @classmethod
    def get_domain_search_is_available(cls, value):
        query = cls.get_query_search_is_available()
        return [('id', 'not in' if value else 'in', query)]
    

class Checkout(metaclass=PoolMeta):
    __name__ = 'library.user.checkout'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.date.domain = []