# Определение моделей базы данных

import json
import uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Script(db.Model):
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f'<Script {self.name}>'


class Step(db.Model):
    # Изменено: id теперь не является единственным первичным ключом
    id = db.Column(db.String(50), nullable=False)
    script_id = db.Column(db.String(50), db.ForeignKey('script.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    # Опции хранятся как JSON-строка
    options_json = db.Column(db.Text, nullable=False, default='[]')
    is_final = db.Column(db.Boolean, default=False)

    # Добавлено: составной первичный ключ (id, script_id)
    __table_args__ = (db.PrimaryKeyConstraint('id', 'script_id'),)

    # Связь с моделью Script
    script = db.relationship('Script', backref=db.backref('steps', lazy=True))

    @property
    def options(self):
        """Возвращает опции как список словарей."""
        return json.loads(self.options_json)

    @options.setter
    def options(self, value):
        """Устанавливает опции из списка словарей, сохраняя как JSON-строку."""
        self.options_json = json.dumps(value)

    def __repr__(self):
        return f'<Step {self.id} for Script {self.script_id}>'


class User(db.Model):
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'operator'
    full_name = db.Column(db.String(100), nullable=False, default='')
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'
