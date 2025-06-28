import sqlite3
from flask import Flask, jsonify, render_template, request
from uuid import uuid4
import time

app = Flask(__name__)

# DB connection
def get_db():
    con = sqlite3.connect('db.db')
    con.row_factory = sqlite3.Row
    return con

# Online users: uuid -> nickname
online = {}
global_chat = []
@app.route('/new', methods=['POST'])
def new_user():
    data = request.json
    if not data or not data.get('nick') or not data.get('password'):
        return 'Missing fields.', 400

    con = get_db()
    cur = con.cursor()
    # Check if user exists
    cur.execute('SELECT * FROM users WHERE nickname = ?', (data['nick'],))
    if cur.fetchone():
        return 'User already exists.', 409

    # Register
    cur.execute('INSERT INTO users VALUES (?, ?)', (data['nick'], data['password']))
    con.commit()

    # Auto-login after registration
    u = uuid4().hex
    online[u] = data['nick']
    print('New UID registered:', u)
    return jsonify({'uuid': u})


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('nick') or not data.get('password'):
        return 'Missing credentials.', 400

    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT * FROM users WHERE nickname = ? AND password = ?', (data['nick'], data['password']))
    if cur.fetchone():
        u = uuid4().hex
        online[u] = data['nick']
        return jsonify({'uuid': u})
    return 'Invalid credentials.', 403


@app.route('/create_chat', methods=['POST'])
def create_chat():
    data = request.json
    if not data or not data.get('uuid') or not data.get('chatname'):
        return 'Missing data.', 400

    if data['uuid'] not in online:
        return 'Invalid UUID.', 403

    chatname = data['chatname']
    owner = online[data['uuid']]

    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT * FROM chats WHERE chatname = ?', (chatname,))
    if cur.fetchone():
        return 'Chat already exists.', 409

    cur.execute('INSERT INTO chats VALUES (?, ?)', (chatname, owner))
    cur.execute('INSERT INTO joins VALUES (?, ?)', (owner, chatname))
    con.commit()

    return 'Chat created.'


@app.route('/join', methods=['POST'])
def join_chat():
    data = request.json
    if not data or not data.get('uuid') or not data.get('chatname'):
        return 'Missing data.', 400

    if data['uuid'] not in online:
        return 'Invalid UUID.', 403

    nick = online[data['uuid']]
    chatname = data['chatname']

    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT * FROM chats WHERE chatname = ?', (chatname,))
    if not cur.fetchone():
        return 'Chat does not exist.', 404

    cur.execute('INSERT INTO joins VALUES (?, ?)', (nick, chatname))
    con.commit()
    return 'Joined.'


@app.route('/send', methods=['POST'])
def send_msg():
    data = request.json
    if not data or not data.get('uuid') or not data.get('chat') or not data.get('msg'):
        return 'Missing fields.', 400

    if data['uuid'] not in online:
        return 'Invalid UUID.', 403

    sender = online[data['uuid']]
    chat = data['chat']
    msg = data['msg'].strip()
    if not msg:
        return 'Empty message.', 400
    now = int(time.time())
    if chat == 'global':
        global_chat.append([len(global_chat), sender, msg, now, 'global'])
        return 'Message sent.'
    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT * FROM joins WHERE user = ? AND groupname = ?', (sender, chat))
    if not cur.fetchone():
        return 'Not a member of the chat.', 403

    msg_id = uuid4().hex
    
    cur.execute('INSERT INTO messages VALUES (?, ?, ?, ?, ?)', (msg_id, sender, msg, now, chat))
    con.commit()
    return 'Message sent.'


@app.route('/get', methods=['GET'])
def get_msgs():
    chat = request.args.get('chat')
    if not chat:
        return 'Missing chat name.', 400

    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT sender, message, date FROM messages WHERE chat = ? ORDER BY date DESC LIMIT 40', (chat,))
    rows = cur.fetchall()
    return jsonify([
        {'sender': r['sender'], 'msg': r['message'], 'time': time.ctime(r['date'])}
        for r in rows[::-1]
    ])


@app.route('/chats', methods=['GET'])
def list_chats():
    con = get_db()
    cur = con.cursor()
    cur.execute('SELECT chatname FROM chats')
    rows = cur.fetchall()
    return jsonify(['global']+[r['chatname'] for r in rows])

@app.route('/stream')
def stream():
    def strm():
        while True:
            if request.args.get('chat', 'global') == 'global':
                # here for globals
                pass
            else:
                # here for others
                con = get_db()
                cur = con.execute('SELECT * FROM messages WHERE chat = ? ORDER BY DESC LIMIT 40', ).fetchall()



@app.route('/me/<uuid>')
def whoami(uuid):
    return jsonify({'nick': online.get(uuid)})


@app.route('/docs')
def docs():
    return render_template('docs.html')

if __name__ == '__main__':
    # Init DB if needed
    with sqlite3.connect('db.db') as con:
        con.execute('CREATE TABLE IF NOT EXISTS users(nickname TEXT, password TEXT)')
        con.execute('CREATE TABLE IF NOT EXISTS joins(user TEXT, groupname TEXT)')
        con.execute('CREATE TABLE IF NOT EXISTS chats(chatname TEXT, owner TEXT)')
        con.execute('CREATE TABLE IF NOT EXISTS messages(id TEXT, sender TEXT, message TEXT, date INTEGER, chat TEXT)')
        con.commit()

    app.run(debug=True)
