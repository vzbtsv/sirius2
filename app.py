from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = '1234321'

USERS_FILE = 'users.json'
TASKS_FILE = 'tasks.json'



def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_tasks(tasks):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)



# def init_demo_tasks():
#     tasks = load_tasks()
#     if not tasks:
#         demo_tasks = [
#             {
#                 'id': 1,
#                 'title': 'Задание 1',
#                 'description': 'пунктуация - легкий уровень',
#                 'difficulty': 'легкий',
#                 'type': 'пунктуация',
#                 'question': 'Солнце светило ярко и птицы пели.',
#                 'answer': 'солнце светило ярко, и птицы пели.',
#                 'created_at': '2024-01-01',
#                 'created_by': 'system'
#             },
#             {
#                 'id': 2,
#                 'title': 'Задание 2',
#                 'description': 'грамматика - средний уровень',
#                 'difficulty': 'средний',
#                 'type': 'грамматика',
#                 'question': 'Я читаю интересную книгу.',
#                 'answer': 'винительный',
#                 'created_at': '2024-01-02',
#                 'created_by': 'system'
#             },
#             {
#                 'id': 3,
#                 'title': 'Задание 3',
#                 'description': 'орфография - сложный уровень',
#                 'difficulty': 'сложный',
#                 'type': 'орфография',
#                 'question': 'Он (не)доумевал по поводу случившегося.',
#                 'answer': 'недоумевал',
#                 'created_at': '2024-01-03',
#                 'created_by': 'system'
#             }
#         ]
#         save_tasks(demo_tasks)


@app.context_processor
def inject_user():
    return dict(current_user=session.get('username'))


@app.route('/')
def index():
    tasks = load_tasks()

    user_data = None
    if 'username' in session:
        username = session['username']
        users = load_users()
        user_data = users.get(username, {})

    return render_template('index.html', tasks=tasks, user_data=user_data)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неверный логин или пароль')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = load_users()

        if username in users:
            return render_template('register.html', error='Пользователь уже существует')

        users[username] = {
            'password': password,
            'created_at': datetime.now().strftime('%Y-%m-%d'),
            'completed_tasks': [],
            'stats': {
                'total_tasks': 0,
                'correct_answers': 0,
                'accuracy': 0
            }
        }

        save_users(users)
        session['username'] = username
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    users = load_users()
    user_data = users.get(username, {})

    return render_template('profile.html',
                           username=username,
                           user_data=user_data)


@app.route('/task/<int:task_id>')
def task_detail(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)

    if not task:
        return redirect(url_for('index'))

    if 'username' not in session:
        return render_template('task_detail.html',
                               task=task,
                               show_question=False,
                               message='Войдите, чтобы начать выполнение задания')

    username = session['username']
    users = load_users()
    user_data = users.get(username, {})
    completed = task_id in user_data.get('completed_tasks', [])

    return render_template('task_detail.html',
                           task=task,
                           show_question=True,
                           completed=completed)


@app.route('/task/<int:task_id>/check', methods=['POST'])
def check_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Требуется авторизация'}), 401

    tasks = load_tasks()
    task = next((t for t in tasks if t.get('id') == task_id), None)

    if not task:
        return jsonify({'error': 'Задание не найдено'}), 404


    data = request.get_json()
    user_answer = data.get('answer', '').strip()
    correct_answer = task.get('answer', '').strip()


    is_correct = user_answer.lower() == correct_answer.lower()

    users = load_users()
    username = session['username']

    if username in users:
        if is_correct and task_id not in users[username].get('completed_tasks', []):
            users[username]['completed_tasks'].append(task_id)

        stats = users[username].get('stats', {})
        stats['total_tasks'] = stats.get('total_tasks', 0) + 1

        if is_correct:
            stats['correct_answers'] = stats.get('correct_answers', 0) + 1

        total = stats.get('total_tasks', 0)
        correct = stats.get('correct_answers', 0)
        if total > 0:
            stats['accuracy'] = round((correct / total) * 100, 2)

        save_users(users)

    return jsonify({
        'is_correct': is_correct,
        'user_answer': user_answer,
        'correct_answer': correct_answer
    })


@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        tasks = load_tasks()

        next_id = max([t.get('id', 0) for t in tasks], default=0) + 1

        task_type = request.form.get('type', '')
        difficulty = request.form.get('difficulty', '')
        question = request.form.get('question', '')
        answer = request.form.get('answer', '')

        if question and answer:
            new_task = {
                'id': next_id,
                'title': f'Задание {next_id}',
                'description': f'{task_type} - {difficulty} уровень',
                'type': task_type,
                'difficulty': difficulty,
                'question': question,
                'answer': answer.strip().lower(),
                'created_at': datetime.now().strftime('%Y-%m-%d'),
                'created_by': session['username']
            }

            tasks.append(new_task)
            save_tasks(tasks)
            return redirect(url_for('index'))
        else:
            return render_template('add_task.html',
                                   error='Пожалуйста, заполните все обязательные поля')

    return render_template('add_task.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    # if not os.path.exists(TASKS_FILE):
    #     init_demo_tasks()

    app.run(debug=True, port=5000)