# 📦 Sistema de Gestión de Inventarios

Aplicación web para registrar productos, controlar entradas y salidas de stock, recibir alertas de stock bajo, consultar un dashboard y exportar reportes en CSV.

**Stack:** Python 3.8+ · Flask · SQLite · Flask-SQLAlchemy · Flask-Login · Bootstrap 5 · Gunicorn

---

## Contenido
1. [Requisitos previos](#1-requisitos-previos)
2. [Ejecución local con entorno virtual](#2-ejecución-local-con-entorno-virtual)
3. [Usuarios y permisos](#3-usuarios-y-permisos)
4. [Funcionalidades](#4-funcionalidades)
5. [Estructura del proyecto](#5-estructura-del-proyecto)
6. [Configuración](#6-configuración)
7. [Despliegue en PythonAnywhere](#7-despliegue-en-pythonanywhere)
8. [Solución de problemas](#8-solución-de-problemas)

---

## 1. Requisitos previos
- Python 3.8 o superior (recomendado 3.10+). Verifique con `python --version` (o `python3 --version`).
- `pip` (viene incluido con Python).
- Conexión a internet la primera vez (para instalar dependencias y cargar Bootstrap desde CDN).

## 2. Ejecución local con entorno virtual

Abra una terminal dentro de la carpeta `sistema_inventario`.

**Windows (PowerShell o CMD)**
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python run.py
```
> Si PowerShell bloquea la activación, ejecute una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Luego abra **http://127.0.0.1:5000** en Chrome, Firefox o Edge.

Notas:
- El prompt mostrará `(venv)` cuando el entorno esté activo.
- Para detener el servidor: `Ctrl + C`. Para salir del entorno: `deactivate`.
- En usos posteriores solo repita **activar entorno + `python run.py`**.
- La base de datos `instance/inventario.db` se crea automáticamente en el primer arranque, con usuarios y categorías de ejemplo. Para reiniciar los datos, detenga la app y borre ese archivo.

**Alternativa tipo producción (Linux/macOS):** `gunicorn run:app`

### Cargar datos de ejemplo (opcional)
Con el entorno virtual activo:
```bash
python seed_datos.py            # agrega categorías, 25 productos y ~60 días de movimientos (no duplica)
python seed_datos.py --reset    # BORRA todo y vuelve a cargar los datos de ejemplo
```
Los datos incluyen productos con stock bajo y agotados para probar las alertas, y un historial coherente con el stock actual.

## 3. Usuarios y permisos

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `cliente` | `cliente123` | Cliente |

⚠️ Cambie estas contraseñas antes de usar el sistema con datos reales.

| Acción | Administrador | Cliente |
|---|:---:|:---:|
| Iniciar/cerrar sesión | ✅ | ✅ |
| Dashboard | ✅ | ✅ |
| Buscar y filtrar productos | ✅ | ✅ |
| Consultar historial | ✅ | ✅ |
| CRUD de productos y categorías | ✅ | ❌ |
| Registrar entradas/salidas | ✅ | ❌ |
| Ver alertas de stock bajo | ✅ | ❌ |
| Exportar reportes CSV | ✅ | ❌ |

## 4. Funcionalidades

| Módulo | Descripción | RF |
|---|---|---|
| Login | Autenticación con contraseñas hasheadas | RF-01 |
| Dashboard | Total de productos, unidades, valor del inventario, alertas y últimos movimientos | RF-08 |
| Productos | CRUD, búsqueda por nombre/SKU y filtro por categoría | RF-02, RF-07 |
| Categorías | CRUD (no se elimina una categoría con productos) | RF-10 |
| Movimientos | Entradas y salidas con validación de stock; historial filtrable | RF-03, RF-04, RF-05 |
| Alertas | Productos con cantidad ≤ stock mínimo (resaltados en amarillo) | RF-06 |
| Reportes | Exportación de productos y movimientos a CSV (compatible con Excel) | RF-09 |

## 5. Estructura del proyecto
```
sistema_inventario/
├── app/
│   ├── __init__.py        # Fábrica de la app y datos iniciales
│   ├── models.py          # Usuario, Categoria, Producto, Movimiento
│   ├── utils.py           # Decorador admin_required
│   ├── routes/            # auth, productos, categorias, movimientos, dashboard, reportes
│   ├── templates/         # Plantillas Jinja2 (Bootstrap 5)
│   └── static/            # css/ y js/
├── instance/inventario.db # Base SQLite (se genera sola)
├── config.py
├── requirements.txt
├── run.py
├── seed_datos.py          # Script para poblar la BD con datos de ejemplo
└── README.md
```

## 6. Configuración
Variables de entorno opcionales:

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave para firmar sesiones. **Defínala en producción.** |

Ejemplos: `export SECRET_KEY="clave-larga-y-aleatoria"` (Linux/macOS) · `set SECRET_KEY=clave-larga-y-aleatoria` (Windows CMD).

## 7. Despliegue en PythonAnywhere
1. Cree una cuenta en pythonanywhere.com y abra una consola **Bash**.
2. Clone o suba el proyecto: `git clone <url-del-repositorio>`.
3. Cree el entorno e instale dependencias:
   ```bash
   mkvirtualenv inventario --python=python3.10
   cd ~/sistema_inventario
   pip install -r requirements.txt
   ```
4. Pestaña **Web** → *Add a new web app* → *Manual configuration* → Python 3.10.
5. En *Virtualenv* escriba `/home/USUARIO/.virtualenvs/inventario`.
6. Edite el archivo WSGI y deje únicamente:
   ```python
   import sys, os
   sys.path.insert(0, '/home/USUARIO/sistema_inventario')
   os.environ['SECRET_KEY'] = 'una-clave-larga-y-aleatoria'
   from run import app as application
   ```
7. En *Static files* agregue: URL `/static/` → Directorio `/home/USUARIO/sistema_inventario/app/static`.
8. Pulse **Reload** y abra `https://USUARIO.pythonanywhere.com`.

(Reemplace `USUARIO` por su nombre de usuario. La base `instance/inventario.db` se crea sola.)

## 8. Solución de problemas

| Problema | Solución |
|---|---|
| `python` no se reconoce (Windows) | Use `py -m venv venv` o reinstale Python marcando *Add to PATH*. |
| `ModuleNotFoundError: flask` | El entorno no está activo; actívelo y repita `pip install -r requirements.txt`. |
| Puerto 5000 ocupado | Cambie en `run.py`: `app.run(debug=True, port=5001)`. |
| La página se ve sin estilos | Bootstrap se carga por CDN; verifique su conexión a internet. |
| Olvidé la contraseña | Detenga la app, borre `instance/inventario.db` y reinicie (se pierden los datos). |
| Error al instalar con Python más nuevo | Ejecute `pip install flask flask-sqlalchemy flask-login gunicorn` sin versiones fijas. |

---
Proyecto académico — Gerencia de Proyectos Informáticos, Politécnico Grancolombiano, 2026.
