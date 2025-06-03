import os
from pathlib import Path
from flask import Flask, redirect, url_for
from flask.cli import load_dotenv
from models import db, Script, Step
from werkzeug.middleware.proxy_fix import ProxyFix
from prefix_middleware import PrefixMiddleware
from routes import operator_bp, admin_bp

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

app = Flask(__name__,
            static_url_path='/static',
            static_folder='static',
            )

# ALWAYS set BEHIND_PROXY to true when running behind nginx
app.config['BEHIND_PROXY'] = True

# Use the prefix regardless of environment
prefix = '/call-center'

# Configure app
app.config.update(
    SERVER_NAME=None,  # Set to None to avoid URL generation issues
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///scripts.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv('SECRET_KEY', 'default-secret-key'),
    PREFERRED_URL_SCHEME='http',
    MAX_CONTENT_LENGTH=100 * 1024 * 1024  # 100MB max upload size
)

# Configure ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configure database
db.init_app(app)

# Import and register blueprints


# Register blueprints with URL prefix
app.register_blueprint(operator_bp, url_prefix='/call-center')
app.register_blueprint(admin_bp, url_prefix='/call-center')

# app.wsgi_app = PrefixMiddleware(app.wsgi_app, app=app, prefix=prefix)

# # Add a root route to redirect to the main page
# @app.route('/')
# def root():
#     return redirect(f"{prefix}/")

# Add a main route
# @app.route('/main')
# def main_redirect():
#     return redirect(f"call-center/")

def create_initial_data():
    with app.app_context():
        # Создаем таблицы, если их нет
        db.create_all()

        # Проверяем, есть ли уже скрипты
        if not Script.query.first():
            print("Создание начальных данных скриптов...")
            # Пример данных для скриптов
            script_welcome_id = "script_welcome"
            script_sales_id = "script_sales"

            welcome_script = Script(id=script_welcome_id, name="Приветственный скрипт")
            sales_script = Script(id=script_sales_id, name="Скрипт продаж продукта Б")

            db.session.add(welcome_script)
            db.session.add(sales_script)
            db.session.commit()

            # Шаги для приветственного скрипта
            steps_welcome = [
                Step(id="start", script_id=script_welcome_id,
                     text="Здравствуйте, меня зовут [ИМЯ ОПЕРАТОРА]. Удобно ли вам сейчас говорить?",
                     options=[
                         {"text": "Да, удобно", "next_step": "purpose_of_call"},
                         {"text": "Нет, неудобно", "next_step": "reschedule"},
                         {"text": "Завершить звонок", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="purpose_of_call", script_id=script_welcome_id,
                     text="Отлично! Я звоню по поводу [ЦЕЛЬ ЗВОНКА].",
                     options=[
                         {"text": "Продолжить", "next_step": "offer_details"},
                         {"text": "Завершить", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="offer_details", script_id=script_welcome_id,
                     text="Мы предлагаем [ДЕТАЛИ ПРЕДЛОЖЕНИЯ].",
                     options=[
                         {"text": "Интересно", "next_step": "next_steps"},
                         {"text": "Неинтересно", "next_step": "handle_objection"}
                     ], is_final=False),
                Step(id="handle_objection", script_id=script_welcome_id,
                     text="Понимаю, что может быть неинтересно. Могу я узнать причину?",
                     options=[
                         {"text": "Узнать причину", "next_step": "address_objection"},
                         {"text": "Завершить", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="address_objection", script_id=script_welcome_id,
                     text="Спасибо за информацию. Мы учтем это. Могу ли я предложить вам что-то еще?",
                     options=[
                         {"text": "Предложить другое", "next_step": "another_offer"},
                         {"text": "Завершить", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="another_offer", script_id=script_welcome_id,
                     text="Как насчет [ДРУГОЕ ПРЕДЛОЖЕНИЕ]?",
                     options=[
                         {"text": "Принять", "next_step": "next_steps"},
                         {"text": "Отказаться", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="next_steps", script_id=script_welcome_id,
                     text="Отлично! Тогда следующий шаг - [СЛЕДУЮЩИЙ ШАГ].",
                     options=[
                         {"text": "Завершить", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="reschedule", script_id=script_welcome_id,
                     text="Хорошо, когда вам будет удобно перезвонить?",
                     options=[
                         {"text": "Назначить время", "next_step": "end_call"},
                         {"text": "Завершить", "next_step": "end_call"}
                     ], is_final=False),
                Step(id="end_call", script_id=script_welcome_id,
                     text="Спасибо за ваше время. До свидания!",
                     options=[], is_final=True)
            ]
            db.session.add_all(steps_welcome)
            db.session.commit()

            # Шаги для скрипта продаж
            steps_sales = [
                Step(id="start", script_id=script_sales_id,
                     text="Добрый день! Меня зовут [ИМЯ ОПЕРАТОРА], я представляю [НАЗВАНИЕ КОМПАНИИ]. Мы проводим опрос по [ТЕМЕ ОПРОСА].",
                     options=[
                         {"text": "Готов ответить", "next_step": "question_1"},
                         {"text": "Нет времени", "next_step": "reschedule_sales"}
                     ], is_final=False),
                Step(id="question_1", script_id=script_sales_id,
                     text="Используете ли вы [ТИП ПРОДУКТА] в своей работе?",
                     options=[
                         {"text": "Да", "next_step": "question_2"},
                         {"text": "Нет", "next_step": "introduce_product_b"}
                     ], is_final=False),
                Step(id="question_2", script_id=script_sales_id,
                     text="Какие основные проблемы вы сталкиваетесь с текущим [ТИП ПРОДУКТА]?",
                     options=[
                         {"text": "Проблема А", "next_step": "solution_a"},
                         {"text": "Проблема Б", "next_step": "solution_b"},
                         {"text": "Другое", "next_step": "solution_general"}
                     ], is_final=False),
                Step(id="introduce_product_b", script_id=script_sales_id,
                     text="Наш продукт Б идеально подходит для решения ваших задач. Он [ОПИСАНИЕ ПРЕИМУЩЕСТВ].",
                     options=[
                         {"text": "Подробнее", "next_step": "features_b"},
                         {"text": "Неинтересно", "next_step": "handle_objection_sales"}
                     ], is_final=False),
                Step(id="reschedule_sales", script_id=script_sales_id,
                     text="Хорошо, когда вам будет удобно обсудить этот вопрос?",
                     options=[
                         {"text": "Назначить время", "next_step": "end_call_sales"},
                         {"text": "Завершить", "next_step": "end_call_sales"}
                     ], is_final=False),
                Step(id="end_call_sales", script_id=script_sales_id,
                     text="Спасибо за ваше время. До свидания!",
                     options=[], is_final=True)
            ]
            db.session.add_all(steps_sales)
            db.session.commit()
            print("Начальные данные скриптов успешно созданы.")
        else:
            print("Скрипты уже существуют в базе данных, начальные данные не создаются.")


if __name__ == '__main__':
    with app.app_context():
        # Create initial data if needed
        from app import create_initial_data
        create_initial_data()
    app.run(host='0.0.0.0', port=80, debug=True)

