#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, abort, session, send_file
import os, json, psutil, subprocess, zipfile, io, datetime
from pathlib import Path
from functools import wraps

BASE_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = BASE_DIR / 'config.json'
LOG_FILE = BASE_DIR / 'activity.log'
ALLOWED_TEXT_EXT = {'.txt', '.log', '.md', '.cfg', '.ini', '.json', '.py', '.csv', '.html', '.css', '.js'}
ALLOWED_IMG_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}

app = Flask(__name__)
app.secret_key = os.environ.get('MINICASAOS_SECRET', 'xchris-ultra-secret-2026')

def load_config():
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
            if "users" not in cfg: cfg["users"] = {"admin": "xchrisadmin123"}
            return cfg
        except: return {"users": {"admin": "xchrisadmin123"}}
    return {"users": {"admin": "xchrisadmin123"}}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def log_action(action):
    ip = request.remote_addr
    user = session.get('username', 'Guest')
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    entry = f"{ip}: Logged in on {user} / {action} at {now}\n"
    # Formato richiesto: 192.x.x.x: Logged in on account / Action
    # Sovrascrivo leggermente per matchare la tua richiesta specifica
    log_line = f"{ip}: {action} (User: {user})\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_line)

def is_safe_path(basedir: Path, path: Path) -> bool:
    try:
        return basedir in path.resolve().parents or path.resolve() == basedir
    except: return False

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'): return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p = request.form.get('username'), request.form.get('password')
        cfg = load_config()
        if u in cfg['users'] and cfg['users'][u] == p:
            session.update({'logged_in': True, 'username': u})
            log_action(f"Logged in on {u}")
            return redirect(url_for('index'))
        flash("Credenziali errate", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    log_action("Logged out")
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    cfg = load_config()
    if not cfg.get('main_dir'): return redirect(url_for('setup'))
    base = Path(cfg['main_dir'])
    if not base.exists(): return redirect(url_for('setup'))
    
    rel = request.args.get('path', '').strip('/')
    target = (base / rel).resolve()
    if not is_safe_path(base, target): return redirect(url_for('index'))
    
    parent_path = str(Path(rel).parent) if rel and Path(rel).parent != Path('.') else ""
    entries = []
    try:
        for p in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            entries.append({'name': p.name, 'is_dir': p.is_dir(), 'ext': p.suffix.lower()})
    except: pass
    
    try: disk = psutil.disk_usage(cfg['main_dir'])
    except: disk = None
    
    return render_template('index.html', entries=entries, rel=rel, parent_path=None if not rel else parent_path,
                           cpu=psutil.cpu_percent(), ram=psutil.virtual_memory(), disk=disk)

@app.route('/view', methods=['GET', 'POST'])
@login_required
def view_file():
    cfg = load_config()
    base = Path(cfg['main_dir'])
    rel, filename = request.args.get('path', ''), request.args.get('file', '')
    file_path = (base / rel / filename).resolve()
    
    if not is_safe_path(base, file_path) or not file_path.exists(): return redirect(url_for('index', path=rel))

    if request.method == 'POST':
        content = request.form.get('content', '').replace('\r\n', '\n')
        try:
            file_path.write_text(content, encoding='utf-8')
            log_action(f"Modified {filename}")
            flash("File salvato!", "success")
        except Exception as e: flash(f"Errore: {e}", "error")
        return redirect(url_for('view_file', path=rel, file=filename))

    ext = file_path.suffix.lower()
    if ext in ALLOWED_IMG_EXT: return render_template('view.html', filename=filename, is_image=True, rel=rel)
    content = file_path.read_text(errors='replace')
    return render_template('view.html', filename=filename, is_image=False, content=content, rel=rel)

@app.route('/cmd', methods=['GET', 'POST'])
@login_required
def cmd():
    cfg = load_config()
    if 'cwd' not in session:
        session['cwd'] = cfg.get('main_dir', str(BASE_DIR))
    
    output = ""
    if request.method == 'POST':
        command = request.form.get('command', '').strip()
        if command:
            log_action(f"Sent the command: {command}")
            if command.startswith("cd "):
                new_path = (Path(session['cwd']) / command[3:].strip()).resolve()
                if new_path.exists() and new_path.is_dir():
                    session['cwd'] = str(new_path)
                    output = f"Cambiata directory in {session['cwd']}"
                else: output = "Errore: Directory non trovata."
            else:
                try:
                    output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, cwd=session['cwd'])
                except subprocess.CalledProcessError as e: output = e.output
                except Exception as e: output = str(e)
    return render_template('cmd.html', output=output, cwd=session['cwd'])

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    cfg = load_config()
    log_action("Opened Settings")
    if request.method == 'POST':
        du = request.form.get('delete_user')
        if du:
            if du != session.get('username') and du in cfg['users']:
                del cfg['users'][du]
                log_action(f"Deleted Account {du}")
        
        nd = request.form.get('main_dir', '').strip()
        if nd: 
            cfg['main_dir'] = str(Path(nd).resolve())
            log_action("Changed Main Directory")

        u, p = request.form.get('username'), request.form.get('password')
        if u and p:
            if u in cfg['users']:
                log_action(f"Changed {u}'s password")
            else:
                log_action(f"Created Account {u}")
            cfg['users'][u] = p
            
        save_config(cfg)
        return redirect(url_for('settings'))
    
    logs = []
    if LOG_FILE.exists():
        logs = LOG_FILE.read_text().splitlines()
    return render_template('settings.html', users=cfg['users'], current_dir=cfg.get('main_dir', ''), logs=logs)

@app.route('/download')
@login_required
def download():
    cfg = load_config()
    base = Path(cfg['main_dir'])
    rel, filename = request.args.get('path', ''), request.args.get('file', '')
    f = (base / rel / filename).resolve()
    if is_safe_path(base, f):
        log_action(f"Downloaded {filename}")
        return send_file(f, as_attachment=True)
    abort(403)

@app.route('/setup', methods=['GET', 'POST'])
@login_required
def setup():
    cfg = load_config()
    if request.method == 'POST':
        p = Path(request.form.get('main_dir', '').strip()).resolve()
        if p.exists() and p.is_dir():
            cfg['main_dir'] = str(p)
            save_config(cfg)
            log_action("System Setup Completed")
            return redirect(url_for('index'))
    return render_template('setup.html', current_dir=cfg.get('main_dir', ''))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)