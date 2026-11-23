# 📦 Sistema de Gestión de Inventarios

Aplicación web para registrar productos, controlar entradas, salidas y ventas, gestionar lotes y vencimientos, registrar mermas y ajustes, recibir alertas de stock bajo, consultar un dashboard con gráficos y exportar reportes en CSV.

**Stack:** Python 3.11 · Flask · SQLite · Flask-SQLAlchemy · Flask-Login · Flask-Migrate · Bootstrap 5 · Chart.js · Gunicorn

---

## Contenido

**Estado:** [implementado y pendiente](#estado-del-proyecto)

1. [Requisitos previos](#1-requisitos-previos)
2. [Ejecución local con entorno virtual](#2-ejecución-local-con-entorno-virtual)
3. [Usuarios y permisos](#3-usuarios-y-permisos)
4. [Funcionalidades](#4-funcionalidades)
5. [Estructura del proyecto](#5-estructura-del-proyecto)
6. [Configuración](#6-configuración)
7. [Despliegue en PythonAnywhere](#7-despliegue-en-pythonanywhere)
8. [Solución de problemas](#8-solución-de-problemas)

---

## Estado del proyecto

- **Implementado:** autenticación y roles, productos, categorías, proveedores, inventario, ventas, lotes y vencimientos, mermas y ajustes, alertas, historial, reportes CSV y dashboard con gráficos.
- **Pendiente:** rotación y sugerencia de pedidos, operación multi-sede, respaldos y despliegue, y cierre de pruebas no funcionales.

El alcance funcional se detalla en la sección [Funcionalidades](#4-funcionalidades).

---

## 1. Requisitos previos
- Python 3.11 (probado con esta versión). Verifique con `python --version` (o `python3 --version`).
- `pip` (viene incluido con Python).
- Conexión a internet la primera vez (para instalar dependencias y cargar Bootstrap y Chart.js desde CDN).

## 2. Ejecución local con entorno virtual

Abra una terminal dentro de la carpeta `sistema_inventario`.

**Windows (PowerShell o CMD)**
```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask --app run.py init-db
python run.py
```
> Si PowerShell bloquea la activación, ejecute una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Linux / macOS**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask --app run.py init-db
python run.py
```

Luego abra **http://127.0.0.1:5000** en Chrome, Firefox o Edge.

Notas:
- El prompt mostrará `(venv)` cuando el entorno esté activo.
- Para detener el servidor: `Ctrl + C`. Para salir del entorno: `deactivate`.
- En usos posteriores solo repita **activar entorno + `python run.py`**.
- `flask --app run.py init-db` aplica las migraciones y crea la sucursal, los usuarios y las categorías base. La base `instance/inventario.db` ya no se crea automáticamente con `create_all`.
- Para reiniciar los datos: detenga la app y ejecute `python seed_datos.py --reset`.

**Alternativa tipo producción (Linux/macOS):** `gunicorn run:app`

### Cargar datos de ejemplo (opcional)
Con el entorno virtual activo:
```bash
python seed_datos.py            # aplica migraciones y agrega categorías, 5 proveedores, 25 productos, 31 lotes y ~60 días de movimientos
python seed_datos.py --reset    # BORRA la BD, aplica migraciones y vuelve a cargar los datos
```
Los datos incluyen productos con stock bajo y agotados para probar las alertas, lotes vencidos y por vencer, y un historial coherente con el stock actual. También se generan mermas y ajustes de demostración.

### Migraciones y pruebas
```bash
flask --app run.py db migrate -m "descripcion del cambio"
flask --app run.py db upgrade
python -m pytest -q
```
La suite actual contiene **46 pruebas** que cubren autenticación, productos, proveedores, inventario, lotes, mermas, dashboard y venta rápida.

## 3. Usuarios y permisos

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Tendero (administrador) |
| `cliente` | `cliente123` | Cajero |

⚠️ Cambie estas contraseñas antes de usar el sistema con datos reales.

| Acción | Tendero | Cajero |
|---|:---:|:---:|
| Iniciar/cerrar sesión | ✅ | ✅ |
| Dashboard | ✅ | ✅ |
| Buscar y filtrar productos | ✅ | ✅ |
| Consultar historial | ✅ | ✅ |
| Registrar venta (venta rápida) | ✅ | ✅ |
| CRUD de productos, categorías y proveedores | ✅ | ❌ |
| Registrar entradas de inventario | ✅ | ❌ |
| Registrar mermas y ajustes | ✅ | ❌ |
| Gestionar lotes y vencimientos | ✅ | ❌ |
| Ver alertas de stock bajo | ✅ | ❌ |
| Exportar reportes CSV | ✅ | ❌ |

## 4. Funcionalidades

| Módulo | Descripción | Requisitos | Estado |
|---|---|---|---|
| Login | Autenticación con contraseñas hasheadas | RF-01 | ✅ |
| Dashboard | Tarjetas generales, actividad del día, gráficos de ventas (7/30 días), top de productos, valor por categoría, estado de lotes, vencimientos y últimos movimientos | RF-08, RF-13 | ✅ |
| Productos | CRUD, búsqueda por nombre/SKU/código de barras, filtros por categoría, proveedor y estado | RF-02, RF-07 | ✅ |
| Categorías | CRUD (no se elimina una categoría con productos) | RF-10 | ✅ |
| Proveedores | CRUD, búsqueda, activación/desactivación y asociación con productos | RF-05 | ✅ |
| Inventario | Entradas con costo unitario y costo promedio ponderado (CPP); el stock solo cambia mediante movimientos | RF-03, RF-05 | ✅ |
| Ventas | Venta rápida para tendero y cajero, con descuento inmediato de stock, consumo FEFO y total estimado | RF-06 | ✅ |
| Movimientos | Entradas, salidas e inventario inicial con stock anterior/nuevo e impacto; historial filtrable | RF-03, RF-04, RF-05 | ✅ |
| Lotes y vencimientos | Registro de lotes en la entrada, salida FEFO, alertas por caducidad y filtros por estado | RF-12 | ✅ |
| Ajustes y mermas | Pérdidas, daños, vencimientos y diferencias de conteo con motivo, usuario e impacto | RF-08 | ✅ |
| Alertas | Productos con cantidad ≤ stock mínimo y lotes vencidos o por vencer | RF-06 | ✅ |
| Reportes | Exportación de productos, movimientos, lotes y mermas a CSV (compatible con Excel) | RF-09 | ✅ |
| Rotación y reposición | Días de inventario y sugerencia de pedido según ventas y tiempo de entrega del proveedor | RF-14 | ⏳ |
| Multi-sede | Stock y movimientos independientes por sucursal, con selector de sede | RNF-06 | ⏳ |
| Respaldos y despliegue | Copias de seguridad, `SECRET_KEY` externa y publicación web | RNF-04, RNF-05 | ⏳ |
| Pruebas no funcionales | Rendimiento, usabilidad y verificación responsiva final | RNF-01, RNF-02, RNF-03 | ⏳ |

**Estado:** ✅ implementado · ⏳ pendiente.

Reglas de negocio del inventario:

- La cantidad de un producto **no se edita directamente**. Se modifica registrando una entrada o una salida.
- Al crear un producto, el “stock inicial” se guarda como movimiento con motivo `inventario_inicial`.
- Cada entrada actualiza el **costo promedio ponderado** (`precio_compra`) salvo que se desmarque la opción en el formulario.
- Cada movimiento guarda stock anterior, stock nuevo, variación (`delta`), costo unitario e impacto valorizado.
- Al registrar una entrada se puede indicar **código de lote y fecha de vencimiento**. Ambos son opcionales, pero deben informarse juntos.
- Las salidas consumen primero el lote con vencimiento más cercano (**FEFO**). Si el stock de lotes no alcanza, el resto se descuenta del stock agregado.
- Cada producto define sus **días de alerta de vencimiento** (15 por defecto).
- Las **mermas** siempre descuentan stock; los **ajustes** pueden aumentarlo o disminuirlo según el conteo físico.
- Una merma o un ajuste negativo no puede dejar el stock en negativo y consume lotes con FEFO.
- La **venta rápida** está disponible para tendero y cajero; descuenta stock de inmediato y no permite vender más de lo disponible.
- Los ingresos del dashboard son estimados con el precio de venta actual del producto.
- Los productos no se eliminan: se **desactivan** para conservar su historial y se pueden reactivar.

## 5. Estructura del proyecto
```
sistema_inventario/
├── app/
│   ├── __init__.py        # Fábrica de la app, extensiones y registro de blueprints
│   ├── cli.py             # Comandos init-db y seed-base
│   ├── models.py          # Usuario, Sucursal, Proveedor, Categoria, Producto, Lote, Movimiento
│   ├── utils.py           # Decorador admin_required
│   ├── services/          # Lógica de inventario (entradas, salidas, ajustes y mermas)
│   ├── routes/            # auth, productos, categorias, proveedores, lotes, movimientos, dashboard, reportes
│   ├── templates/         # Plantillas Jinja2 (Bootstrap 5)
│   └── static/            # css/ y js/
├── migrations/            # Migraciones Alembic/Flask-Migrate
├── tests/                 # Pruebas con pytest
├── instance/inventario.db # Base SQLite (se crea con las migraciones)
├── config.py
├── requirements.txt
├── run.py
├── wsgi.py                # Punto de entrada WSGI para producción
├── seed_datos.py          # Script para poblar la BD con datos de ejemplo
├── pytest.ini
└── README.md
```

## 6. Configuración
Variables de entorno opcionales:

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave para firmar sesiones. **Defínala en producción.** |

Ejemplos: `export SECRET_KEY="clave-larga-y-aleatoria"` (Linux/macOS) · `set SECRET_KEY=clave-larga-y-aleatoria` (Windows CMD).

## 7. Despliegue en PythonAnywhere

PythonAnywhere es una opción adecuada para este proyecto porque conserva el archivo SQLite (`instance/inventario.db`) entre despliegues.

### 7.1 Publicar por primera vez

1. Cree una cuenta en [pythonanywhere.com](https://www.pythonanywhere.com) y abra una consola **Bash**.
2. Clone el repositorio y entre a la carpeta:
   ```bash
   git clone https://github.com/NicolasSRC/Sistem-Inventario.git
   cd Sistem-Inventario
   ```
3. Cree el entorno virtual e instale las dependencias:
   ```bash
   mkvirtualenv inventario --python=python3.11
   pip install -r requirements.txt
   ```
   Si Python 3.11 no está disponible, use `--python=python3.10`.
4. Cree el archivo de configuración y genere una clave secreta:
   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"
   nano .env
   ```
   En `.env` ajuste:
   ```env
   SECRET_KEY=la-clave-generada
   FLASK_APP=run.py
   FLASK_DEBUG=0
   ```
5. Cree o actualice la base de datos y cargue los datos de demostración:
   ```bash
   flask --app run.py db upgrade
   python seed_datos.py
   ```
   `python seed_datos.py --reset` borra y vuelve a crear la base; úselo solo si desea reiniciar los datos.
6. En la pestaña **Web** elija *Add a new web app* → *Manual configuration* → **Python 3.11**.
7. En **Virtualenv** escriba:
   ```text
   /home/USUARIO/.virtualenvs/inventario
   ```
8. Abra el archivo **WSGI** y reemplácelo por:
   ```python
   import sys

   path = "/home/USUARIO/Sistem-Inventario"
   if path not in sys.path:
       sys.path.insert(0, path)

   from wsgi import application
   ```
9. En **Static files** agregue:
   ```text
   URL:       /static/
   Directory: /home/USUARIO/Sistem-Inventario/app/static
   ```
10. Pulse **Reload** y abra `https://USUARIO.pythonanywhere.com`.

Reemplace `USUARIO` por su nombre de usuario en todos los pasos.

### 7.2 Actualizar una versión ya publicada

```bash
cd ~/Sistem-Inventario
git pull
pip install -r requirements.txt
flask --app run.py db upgrade
```

Después pulse **Reload** en la pestaña **Web**. Los datos de SQLite se conservan.

### 7.3 Seguridad después de publicar

El seed crea las cuentas de demostración. Cámbielas antes de compartir la URL:

```bash
flask --app run.py shell
```

```python
from app import db
from app.models import Usuario

admin = Usuario.query.filter_by(username="admin").first()
admin.set_password("NUEVA_CLAVE_SEGURA")
db.session.commit()
```

### 7.4 Otras plataformas

El proyecto incluye `wsgi.py`, por lo que también puede ejecutarse con:

```bash
gunicorn wsgi:application
```

En Render, Railway u otro servicio con sistema de archivos efímero, SQLite se perdería en cada despliegue. En ese caso configure un **volumen persistente** para `instance/` o migre la base a PostgreSQL.

## 8. Solución de problemas

| Problema | Solución |
|---|---|
| `python` no se reconoce (Windows) | Use `py -m venv venv` o reinstale Python marcando *Add to PATH*. |
| `ModuleNotFoundError: flask` | El entorno no está activo; actívelo y repita `pip install -r requirements.txt`. |
| Puerto 5000 ocupado | Cambie en `run.py`: `app.run(debug=True, port=5001)`. |
| La página se ve sin estilos | Bootstrap y Chart.js se cargan por CDN; verifique su conexión a internet. |
| Los gráficos del dashboard no aparecen | Confirme que Chart.js pueda descargarse desde `cdn.jsdelivr.net`; el resto del panel funciona sin los gráficos. |
| Olvidé la contraseña | Detenga la app, borre `instance/inventario.db`, ejecute `flask --app run.py init-db` y reinicie (se pierden los datos). |
| Error al instalar con Python más nuevo | Ejecute `pip install flask flask-sqlalchemy flask-login gunicorn` sin versiones fijas. |

---
Proyecto académico — Emprendimiento de base tecnológica, Politécnico Grancolombiano, 2026.
