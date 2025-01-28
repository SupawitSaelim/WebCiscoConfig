# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

a = Analysis(
   ['app.py'],
   pathex=[],
   binaries=[],
   datas=[
       ('templates', 'templates'),
       ('static', 'static'),
       ('static/snmp/*', 'static/snmp'),
       ('config', 'config'),
       ('core', 'core'),
       ('models/ml/lr_model.pkl', 'models/ml'),
       ('models/ml/dt_model.pkl', 'models/ml'), 
       ('models/ml/rf_model.pkl', 'models/ml'),
       ('node_modules', 'node_modules'),
       ('package.json', 'package.json'),
       ('package-lock.json', 'package-lock.json'),
       ('routes', 'routes'),
       ('utils', 'utils'),
       ('.env', '.')
   ],
    hiddenimports=[
        'engineio.async_drivers.threading',
        'eventlet',
        'flask_socketio',
        'python_socketio',
        'flask_socketio.async_mode.threading',
        'socketio',
        'engineio', 
        'bidict',
        'pymongo',
        'pyserial',
        'numpy',
        'numpy.core.multiarray',
        'sklearn',
        'sklearn.utils._cython_blas',
        'sklearn.neighbors.typedefs',
        'sklearn.neighbors.quad_tree',
        'sklearn.tree._utils',
        'sklearn.utils._typedefs',
        'netmiko',
        'paramiko',
        'textfsm',
        'ntc_templates',
        'APScheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.interval',
        'pandas',
        'joblib',
        'pytz',
        'flask',
        'flask.templating',
        'flask_login',
        'flask_mongoengine',
        'flask_wtf',
        'flask_bcrypt',
        'jinja2',
        'jinja2.ext',
        'email_validator',
        'werkzeug',
        'itsdangerous',
        'click',
        'flask.blueprints',
        'flask_session',
    ],
   hookspath=[],
   hooksconfig={},
   runtime_hooks=[],
   excludes=[],
   win_no_prefer_redirects=False,
   win_private_assemblies=False,
   cipher=block_cipher,
   noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,        # Include these
    a.zipfiles,        # Include these  
    a.datas,           # Include these
    [],
    name='NetworkAutomation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='site.ico'
)

coll = COLLECT(exe,
   a.binaries,
   a.zipfiles,
   a.datas,
   strip=False,
   upx=True,
   upx_exclude=[],
   name='NetworkAutomation',
)