# 📦 Sistema de Gestión de Inventarios

Aplicación web para registrar productos, controlar entradas, salidas y ventas, gestionar lotes y vencimientos, registrar mermas y ajustes, recibir alertas de stock bajo, consultar un dashboard con gráficos, operar varias sucursales de forma independiente y exportar reportes en CSV.

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

- **Implementado:** autenticación y roles, productos, categorías, proveedores, inventario, ventas, lotes y vencimientos, mermas y ajustes, alertas, historial, reportes CSV, rotación con sugerencia de pedidos, dashboard con gráficos, operación multi-sede con aislamiento por sucursal y panel administrativo para usuarios y sucursales.
- **Pendiente:** respaldos, seguridad y despliegue, y cierre de pruebas no funcionales.

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
python seed_datos.py            # aplica migraciones y agrega categorías, 5 proveedores, 2 sucursales, 30 productos, 39 lotes y ~350 movimientos
python seed_datos.py --reset    # BORRA la BD, aplica migraciones y vuelve a cargar los datos
```
Los datos incluyen productos con stock bajo y agotados para probar las alertas, lotes vencidos y por vencer, un historial coherente con el stock actual y una segunda sede (“Sucursal Norte”) con catálogo y movimientos propios. También se generan mermas y ajustes de demostración.

### Migraciones y pruebas
```bash
flask --app run.py db migrate -m "descripcion del cambio"
flask --app run.py db upgrade
python -m pytest -q
```
La suite actual contiene **77 pruebas** que cubren autenticación, productos, proveedores, inventario, lotes, mermas, dashboard, venta rápida, rotación, aislamiento multi-sede y panel administrativo.

## 3. Usuarios y permisos

| Usuario | Contraseña | Rol | Sucursal |
|---|---|---|---|
| `admin` | `admin123` | Tendero (administrador) | Principal |
| `cliente` | `cliente123` | Cajero | Principal |
| `norte` | `norte123` | Cajero | Sucursal Norte |

El login muestra estas cuentas de demostración con su rol y sucursal. Desde **Panel administrativo** el tendero puede registrar nuevas cuentas, asignarles rol y sede, y crear o administrar sucursales.

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
| Consultar rotación y sugerencia de pedidos | ✅ | ❌ |
| Exportar reportes CSV | ✅ | ❌ |
| Cambiar de sucursal activa | ✅ | ❌ (opera en la sede asignada) |
| Gestionar usuarios y sucursales | ✅ | ❌ |

El tendero puede alternar la sucursal activa desde el menú lateral. Todas las consultas, reportes, alertas, movimientos y el dashboard se filtran por esa sede; el cajero siempre opera sobre la sucursal asignada a su usuario.

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
| Rotación y reposición | Mayor y menor rotación, días de inventario y pedido sugerido según ventas, tiempo de entrega y stock mínimo, con vista en pantalla y CSV | RF-14 | ✅ |
| Multi-sede | Stock, lotes y movimientos independientes por sucursal; el tendero cambia la sede activa desde el menú y el cajero queda fijo a la suya | RNF-06 | ✅ |
| Panel administrativo | Registro y edición de usuarios (rol, sede y contraseña), alta y edición de sucursales, activación/desactivación segura y resumen general | RF-01, RF-02, RNF-06 | ✅ |
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
- La **rotación** se calcula con las salidas reales de 7, 30 o 90 días y se clasifica por el promedio vendido por día: alta (≥ 1), media (≥ 0.2), baja (> 0) y sin rotación (0).
- El **pedido sugerido** cubre el consumo durante el tiempo de entrega del proveedor más 7 días de stock de seguridad, sin bajar del stock mínimo del producto.
- Los ingresos del dashboard son estimados con el precio de venta actual del producto.
- Cada producto, lote y movimiento pertenece a una **sucursal**. El stock se controla por producto dentro de su sede.
- El tendero elige la sucursal activa en el menú lateral; el cajero siempre opera en la sucursal de su usuario.
- Un producto de otra sede no se puede editar, vender, ajustar ni registrar en movimientos (responde 404 o rechaza la operación).
- Los SKU y códigos de barras siguen siendo únicos a nivel global, aunque el producto pertenezca a una sede distinta.
- Los usuarios no se eliminan: se editan para conservar la trazabilidad de sus movimientos. El tendero no puede quitarse a sí mismo el rol de administrador.
- Una sucursal con productos o usuarios asignados no se puede desactivar; solo las sucursales activas aparecen en el selector de sede.
- Los productos no se eliminan: se **desactivan** para conservar su historial y se pueden reactivar.

## 5. Estructura del proyecto
```
sistema_inventario/
├── app/
│   ├── __init__.py        # Fábrica de la app, extensiones y registro de blueprints
│   ├── cli.py             # Comandos init-db y seed-base
│   ├── models.py          # Usuario, Sucursal, Proveedor, Categoria, Producto, Lote, Movimiento
│   ├── utils.py           # Decorador admin_required
│   ├── services/          # Lógica de inventario, rotación y resolución de sucursal activa
│   ├── routes/            # auth, productos, categorias, proveedores, lotes, movimientos, dashboard, reportes, sucursales, admin
│   ├── templates/         # Plantillas Jinja2 (Bootstrap 5), incluye admin/
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
workon inventario          # activa el entorno virtual creado en el paso 7.1
git pull
pip install -r requirements.txt
flask --app run.py db upgrade
```

Si `workon` no está disponible, active el entorno con su ruta:

```bash
source ~/.virtualenvs/inventario/bin/activate
```

El entorno virtual debe estar activo para que `pip` instale en el lugar correcto y para que el comando `flask` exista. `git pull` no lo requiere, pero el resto de la actualización sí.

Después pulse **Reload** en la pestaña **Web**. Los datos de SQLite se conservan.

### 7.3 Actualizar los datos de la instancia publicada

`flask --app run.py db upgrade` actualiza la estructura de la base, pero **no agrega datos de demostración ni sucursales nuevas**. Antes de cambiar datos, haga un respaldo:

```bash
cd ~/Sistem-Inventario
cp instance/inventario.db ~/inventario-respaldo-$(date +%F-%H%M).db
```

**Opción A — Cargar los datos de demostración pendientes (sin borrar nada):**

```bash
python seed_datos.py
```

El script es idempotente: crea la “Sucursal Norte”, sus productos `NOR-*`, el usuario `norte/norte123` y cualquier categoría, proveedor o producto que falte. **No use `python seed_datos.py --reset` en una instancia publicada**, porque borra `instance/inventario.db` antes de volver a poblarla.

**Opción B — Datos reales desde la aplicación (recomendado):**

1. Ingrese como `admin`.
2. Abra **Panel administrativo** en el menú lateral.
3. Registre los usuarios y las sucursales que necesite.
4. Registre productos, entradas y movimientos desde sus módulos habituales.

**Opción C — Datos puntuales desde la consola:**

```bash
flask --app run.py shell
```

```python
from app import db
from app.models import Sucursal, Usuario

sucursal = Sucursal(nombre="Sucursal Centro", direccion="Calle 10 #20-30", telefono="3001234567")
db.session.add(sucursal)
db.session.flush()

usuario = Usuario(username="centro", rol="cajero", sucursal=sucursal)
usuario.set_password("una-clave-segura")
db.session.add(usuario)
db.session.commit()
```

Al terminar, pulse **Reload** en la pestaña **Web**.

### 7.4 Seguridad después de publicar

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

### 7.5 Otras plataformas

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
