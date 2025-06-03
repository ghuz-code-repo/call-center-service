# app.py
import base64
from flask import Blueprint, app, render_template, request, jsonify, redirect, url_for, flash
import uuid

from models import Script, Step, User, db

# !!! ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ ЭТО НА ПРОДАКШЕНЕ НА СЛУЧАЙНЫЙ И ДЛИННЫЙ КЛЮЧ !!!
operator_bp = Blueprint('operator', __name__)
admin_bp = Blueprint('admin', __name__)



def decode_header_full_name(request):
    """
    Декодирует base64-закодированное полное имя из заголовков запроса
    
    Args:
        request: Объект запроса Flask с заголовками
        
    Returns:
        str: Декодированное полное имя или оригинальное значение, если не закодировано
    """
    # Получаем закодированное имя и флаг кодировки
    encoded_full_name = request.headers.get('X-User-Full-Name', '')
    encoding = request.headers.get('X-User-Full-Name-Encoding', '')
    
    print(f"Received full name header: {encoded_full_name}, encoding: {encoding}")
    
    if encoding == 'base64' and encoded_full_name:
        try:
            # Декодируем base64
            decoded_bytes = base64.b64decode(encoded_full_name)
            decoded_name = decoded_bytes.decode('utf-8')
            print(f"Decoded name: '{decoded_name}'")
            return decoded_name
        except Exception as e:
            print(f"Error decoding full name: {e}")
            return encoded_full_name  # Возвращаем как есть, если декодирование не удалось
    else:
        return encoded_full_name  # Не закодировано или нет указания кодировки

def get_current_user():
    """Get current user information from request headers"""
    # Получение имени пользователя из заголовка аутентификации
    username = request.headers.get('X-User-Name')
    # Поиск пользователя в базе данных
    user = User.query.filter_by(username=username).first()
    
    is_admin = request.headers.get('X-User-Admin', 'false').lower() == 'true'
    full_name = decode_header_full_name(request)

    role_str = request.headers.get('X-User-Roles')
    roles = str.split(role_str, ',')
    role=''
    if 'admin' in roles or 'call-center-admin' in roles:
        role = 'admin'
    elif 'call-center-operator' in roles or 'user' in roles:
        role = 'user'
    if user:
        if user.role != 'admin' and is_admin:
            user.role = 'admin'
            db.session.commit()
    print(f"User found: {user}, is_admin: {is_admin}")
    # Если пользователь не найден, но у него есть доступ через шлюз (т.е. заголовок X-User-Name присутствует),
    # создаем нового пользователя в базе данных
    if not user and username:
        # Получаем дополнительную информацию из заголовков и декодируем Base64 если нужно
        full_name = decode_header_full_name(request)
        
        # Создаем нового пользователя с декодированным полным именем
        user = User(
            username=username,
            full_name=full_name,
            role=role,
        )
        db.session.add(user)
        
    if user and ( user.full_name!=full_name):
        user.full_name = full_name
    if user and (user.role != role):
        user.role = role
    try:
        db.session.commit()  # This should set the user.id
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {str(e)}")
    return user

@operator_bp.route('/')
def index():
    """
    Главная страница приложения.
    Перенаправляет на страницу входа, если пользователь не аутентифицирован.
    """
    return render_template('index.html', current_user=get_current_user())

@operator_bp.route('/operator')
def operator_interface():
    """
    Интерфейс оператора.
    Доступен только для аутентифицированных пользователей с ролью 'operator' или 'admin'.
    """
    current_user = get_current_user()

    scripts_data = {}
    try:
        scripts = Script.query.all()
        for script in scripts:
            scripts_data[script.id] = {"name": script.name}
    except Exception as e:
        print(f"Ошибка при получении списка скриптов: {e}")
        scripts_data = {"error": "Не удалось загрузить скрипты"}
    return render_template('operator.html', scripts=scripts_data, current_user=current_user)


@operator_bp.route('/api/get_step/<script_id>/<step_id>')
def get_step(script_id, step_id):
    """
    API-эндпоинт для получения данных о конкретном шаге скрипта.
    Используется фронтендом оператора для динамической загрузки шагов.
    """
    # Проверка роли не нужна, так как оператор уже имеет доступ к интерфейсу
    try:
        step = Step.query.filter_by(script_id=script_id, id=step_id).first()
        if not step:
            return jsonify({"error": "Шаг скрипта не найден"}), 404

        return jsonify({
            "text": step.text,
            "options": step.options,
            "is_final": step.is_final
        })
    except Exception as e:
        print(f"Ошибка при получении шага: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/admin')
def admin_interface():
    """
    Интерфейс администратора.
    Доступен только для аутентифицированных пользователей с ролью 'admin'.
    """
    current_user = get_current_user()
    if current_user.role != 'admin':
        flash('У вас нет прав доступа к этой странице.', 'danger')
        return redirect(url_for('operator.index'))

    scripts_data = {}
    try:
        scripts = Script.query.all()
        for script in scripts:
            scripts_data[script.id] = {"name": script.name}
    except Exception as e:
        print(f"Ошибка при получении списка скриптов: {e}")
        scripts_data = {"error": "Не удалось загрузить скрипты"}
    return render_template('admin.html', scripts=scripts_data, current_user=current_user)


@admin_bp.route('/admin/save_step', methods=['POST'])
def save_step():
    """
    API-эндпоинт для сохранения или обновления шага скрипта.
    Принимает данные шага в формате JSON.
    """
    current_user = get_current_user()

    if current_user.role != 'admin':
        return jsonify({"error": "У вас нет прав для выполнения этой операции."}), 403

    data = request.get_json()
    script_id = data.get('script_id')
    step_id = data.get('step_id')
    text = data.get('text')
    options = data.get('options')
    is_final = data.get('is_final', False)

    if not all([script_id, step_id, text, options is not None]):
        return jsonify({"error": "Отсутствуют необходимые данные"}), 400

    if not isinstance(options, list) or \
            not all(isinstance(opt, dict) and 'text' in opt and 'next_step' in opt for opt in options):
        return jsonify(
            {"error": "Неверный формат опций: опции должны быть списком объектов с полями 'text' и 'next_step'"}), 400

    try:
        script = Script.query.get(script_id)
        if not script:
            return jsonify({"error": "Скрипт не найден"}), 404

        step = Step.query.filter_by(script_id=script_id, id=step_id).first()
        if step:
            step.text = text
            step.options = options
            step.is_final = is_final
        else:
            step = Step(id=step_id, script_id=script_id, text=text, options=options, is_final=is_final)
            db.session.add(step)

        db.session.commit()
        return jsonify({"message": "Шаг успешно сохранен", "script_id": script_id, "step_id": step_id})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при сохранении шага: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/admin/add_script', methods=['POST'])
def add_script():
    """
    API-эндпоинт для добавления нового скрипта.
    Принимает название скрипта.
    Автоматически создает первый шаг 'start'.
    """
    current_user = get_current_user()
    if current_user.role != 'admin':
        return jsonify({"error": "У вас нет прав для выполнения этой операции."}), 403

    data = request.get_json()
    script_name = data.get('script_name')

    if not script_name:
        return jsonify({"error": "Название скрипта не может быть пустым"}), 400

    try:
        new_script_id = f"script_{uuid.uuid4().hex[:8]}"
        new_script = Script(id=new_script_id, name=script_name)
        db.session.add(new_script)
        db.session.commit()

        start_step = Step(id="start", script_id=new_script_id,
                          text=f"Начало скрипта '{script_name}'.",
                          options=[], is_final=False)
        db.session.add(start_step)
        db.session.commit()

        return jsonify({"message": "Скрипт успешно добавлен", "script_id": new_script_id, "script_name": script_name})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении скрипта: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/admin/add_step', methods=['POST'])
def add_step():
    """
    API-эндпоинт для добавления нового шага к существующему скрипту.
    Принимает script_id и опционально text и options.
    """
    current_user = get_current_user()
    if current_user.role != 'admin':
        return jsonify({"error": "У вас нет прав для выполнения этой операции."}), 403

    data = request.get_json()
    script_id = data.get('script_id')
    new_step_id = data.get('new_step_id')
    text = data.get('text', 'Новый шаг')
    options = data.get('options', [])
    is_final = data.get('is_final', False)

    if not all([script_id, new_step_id]):
        return jsonify({"error": "Отсутствуют необходимые данные (script_id, new_step_id)"}), 400

    if not isinstance(options, list) or \
            not all(isinstance(opt, dict) and 'text' in opt and 'next_step' in opt for opt in options):
        return jsonify(
            {"error": "Неверный формат опций: опции должны быть списком объектов с полями 'text' и 'next_step'"}), 400

    try:
        script = Script.query.get(script_id)
        if not script:
            return jsonify({"error": "Скрипт не найден"}), 404

        existing_step = Step.query.filter_by(script_id=script_id, id=new_step_id).first()
        if existing_step:
            return jsonify({"error": "Шаг с таким ID уже существует в этом скрипте"}), 409

        new_step = Step(id=new_step_id, script_id=script_id, text=text, options=options, is_final=is_final)
        db.session.add(new_step)
        db.session.commit()
        return jsonify({"message": "Шаг успешно добавлен", "script_id": script_id, "step_id": new_step_id})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при добавлении шага: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/admin/delete_step', methods=['POST'])
def delete_step():
    """
    API-эндпоинт для удаления шага из скрипта.
    Принимает script_id и step_id.
    """
    current_user = get_current_user()
    
    if current_user.role != 'admin':
        return jsonify({"error": "У вас нет прав для выполнения этой операции."}), 403

    data = request.get_json()
    script_id = data.get('script_id')
    step_id = data.get('step_id')

    if not all([script_id, step_id]):
        return jsonify({"error": "Отсутствуют необходимые данные"}), 400

    try:
        script = Script.query.get(script_id)
        if not script:
            return jsonify({"error": "Скрипт не найден"}), 404

        step_to_delete = Step.query.filter_by(script_id=script_id, id=step_id).first()
        if not step_to_delete:
            return jsonify({"error": "Шаг не найден в скрипте"}), 404

        all_steps_in_script = Step.query.filter_by(script_id=script_id).all()
        for s in all_steps_in_script:
            if s.id == step_id:
                continue
            for option in s.options:
                if option.get("next_step") == step_id:
                    return jsonify(
                        {"error": f"Шаг '{step_id}' является целевым для шага '{s.id}'. Сначала измените ссылки."}), 400

        db.session.delete(step_to_delete)
        db.session.commit()
        return jsonify({"message": "Шаг успешно удален", "script_id": script_id, "step_id": step_id})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при удалении шага: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/admin/delete_script', methods=['POST'])
def delete_script():
    """
    API-эндпоинт для удаления скрипта.
    Принимает script_id.
    """
    current_user = get_current_user()
    
    if current_user.role != 'admin':
        return jsonify({"error": "У вас нет прав для выполнения этой операции."}), 403

    data = request.get_json()
    script_id = data.get('script_id')

    if not script_id:
        return jsonify({"error": "Отсутствует ID скрипта"}), 400

    try:
        script_to_delete = Script.query.get(script_id)
        if not script_to_delete:
            return jsonify({"error": "Скрипт не найден"}), 404

        Step.query.filter_by(script_id=script_id).delete()
        db.session.delete(script_to_delete)
        db.session.commit()
        return jsonify({"message": "Скрипт успешно удален", "script_id": script_id})
    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при удалении скрипта: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500


@admin_bp.route('/api/get_script_steps/<script_id>')
def get_script_steps(script_id):
    """
    API-эндпоинт для получения всех шагов конкретного скрипта.
    Используется фронтендом администратора для заполнения списка шагов.
    """
    # Проверка роли не нужна, так как админ уже имеет доступ к интерфейсу
    try:
        script = Script.query.get(script_id)
        if not script:
            return jsonify({"error": "Скрипт не найден"}), 404

        steps_data = {}
        for step in script.steps:
            steps_data[step.id] = {
                "text": step.text,
                "options": step.options,
                "is_final": step.is_final
            }
        return jsonify(steps_data)
    except Exception as e:
        print(f"Ошибка при получении шагов скрипта: {e}")
        return jsonify({"error": f"Ошибка сервера: {e}"}), 500
