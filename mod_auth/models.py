import string

from passlib.apps import custom_app_context as pwd_context
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from database import Base


class Role(Base):
    __tablename__ = 'role'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    users = relationship("User", back_populates="role")
    pages = relationship("Page", secondary='page_access',
                         back_populates="roles")

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Role %r>' % self.name

    @hybrid_property
    def is_admin(self):
        return self.name == 'Admin'

    @is_admin.expression
    def is_al(cls):
        return cls.name.__eq__('Admin')


class Page(Base):
    __tablename__ = 'page'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    pretty_name = Column(String(75), unique=True)
    global_access = Column(Boolean())
    roles = relationship("Role", secondary='page_access',
                         back_populates="pages")

    def __init__(self, name, pretty_name, global_access=False):
        self.name = name
        self.pretty_name = pretty_name
        self.global_access = global_access

    @hybrid_property
    def is_global(self):
        return self.global_access

    def __repr__(self):
        return '<Page %r>' % self.name


class PageAccess(Base):
    __tablename__ = 'page_access'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    page_id = Column(Integer, ForeignKey('page.id', onupdate="CASCADE",
                                         ondelete="CASCADE"),
                     primary_key=True)
    role_id = Column(Integer, ForeignKey('role.id', onupdate="CASCADE",
                                         ondelete="CASCADE"),
                     primary_key=True)

    def __init__(self, page_id, role_id):
        self.page_id = page_id
        self.role_id = role_id

    def __repr__(self):
        return '<PageAccess %r,%r>' % (self.page_id, self.role_id)


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)
    email = Column(String(191), unique=True, nullable=True)
    password = Column(String(255), unique=False, nullable=False)
    role_id = Column(Integer, ForeignKey('role.id', onupdate="RESTRICT",
                                         ondelete="RESTRICT"), nullable=False)
    role = relationship("Role", back_populates="users")

    def __init__(self, role_id, name, email=None, password=''):
        self.name = name
        self.email = email
        self.password = password
        self.role_id = role_id

    def __repr__(self):
        return '<User %r>' % self.name

    @staticmethod
    def generate_hash(password):
        # Go for increased strength no matter what
        return pwd_context.encrypt(password, category='admin')

    @staticmethod
    def create_random_password(length=16):
        chars = string.ascii_letters + string.digits + '!@#$%^&*()'
        import os
        return ''.join(chars[ord(os.urandom(1)) % len(chars)] for i in
                       range(length))

    def is_password_valid(self, password):
        return pwd_context.verify(password, self.password)

    def update_password(self, new_password):
        self.password = self.generate_hash(new_password)

    def is_admin(self):
        if self.role is not None:
            return self.role.is_admin
        return False

    def can_access_route(self, route):
        page = Page.query.filter(Page.name == route).first()
        return self.is_admin() or (page is not None and (
            page.global_access or page in self.role.pages))
