"""Puebla la base de datos con datos de ejemplo.

Uso:
    python seed_datos.py            # agrega los datos que falten (no duplica)
    python seed_datos.py --reset    # BORRA todo y vuelve a crear los datos
"""
import argparse
import random
from datetime import datetime, timedelta

from app import create_app, db
from app.models import Usuario, Categoria, Producto, Movimiento

USUARIOS = [("admin", "admin123", "administrador"), ("cliente", "cliente123", "cliente")]
CATEGORIAS = ["General", "Electrónica", "Papelería", "Hogar", "Herramientas", "Aseo", "Alimentos"]

# (nombre, sku, categoría, precio, stock_minimo, descripción)
PRODUCTOS = [
    ("Mouse inalámbrico", "ELE-001", "Electrónica", 45000, 10, "Mouse óptico 2.4 GHz"),
    ("Teclado USB", "ELE-002", "Electrónica", 68000, 8, "Teclado en español, 104 teclas"),
    ("Audífonos con micrófono", "ELE-003", "Electrónica", 89000, 8, "Diadema, conector 3.5 mm"),
    ("Cable HDMI 2 m", "ELE-004", "Electrónica", 22000, 15, "Cable HDMI 4K"),
    ("Memoria USB 64 GB", "ELE-005", "Electrónica", 38000, 12, "USB 3.0"),
    ("Cargador USB-C 20 W", "ELE-006", "Electrónica", 52000, 10, "Carga rápida"),
    ("Resma papel carta", "PAP-001", "Papelería", 18500, 20, "500 hojas, 75 g"),
    ("Bolígrafo azul (caja x12)", "PAP-002", "Papelería", 14000, 15, "Punta media 1.0 mm"),
    ("Cuaderno 100 hojas", "PAP-003", "Papelería", 6500, 25, "Cuadriculado, tapa dura"),
    ("Marcadores permanentes x4", "PAP-004", "Papelería", 12000, 10, "Colores surtidos"),
    ("Carpeta archivadora", "PAP-005", "Papelería", 9800, 12, "Tamaño oficio, lomo ancho"),
    ("Lámpara LED de escritorio", "HOG-001", "Hogar", 74000, 6, "Luz cálida/fría regulable"),
    ("Juego de toallas x3", "HOG-002", "Hogar", 59000, 6, "Algodón 450 g"),
    ("Organizador plástico", "HOG-003", "Hogar", 31000, 8, "Con tapa, 30 L"),
    ("Taladro percutor 600 W", "HER-001", "Herramientas", 235000, 4, "Incluye maletín y brocas"),
    ("Juego de destornilladores x6", "HER-002", "Herramientas", 28000, 8, "Punta imantada"),
    ("Cinta métrica 5 m", "HER-003", "Herramientas", 15000, 10, "Carcasa antigolpes"),
    ("Martillo de uña", "HER-004", "Herramientas", 24500, 6, "Mango de fibra"),
    ("Detergente líquido 3 L", "ASE-001", "Aseo", 29000, 12, "Multiusos"),
    ("Desinfectante 1 L", "ASE-002", "Aseo", 11500, 15, "Aroma lavanda"),
    ("Papel higiénico x12", "ASE-003", "Aseo", 21000, 20, "Doble hoja"),
    ("Café molido 500 g", "ALI-001", "Alimentos", 19500, 15, "Tostión media"),
    ("Azúcar 1 kg", "ALI-002", "Alimentos", 4800, 25, "Refinada"),
    ("Arroz 5 kg", "ALI-003", "Alimentos", 21500, 15, "Grano largo"),
    ("Aceite vegetal 3 L", "ALI-004", "Alimentos", 36000, 10, "Girasol"),
]

OBS_ENTRADA = ["Compra a proveedor", "Reposición de inventario", "Devolución de cliente", "Ajuste de inventario"]
OBS_SALIDA = ["Venta mostrador", "Venta en línea", "Consumo interno", "Pedido de cliente", "Producto dañado"]


def asegurar_usuarios():
    for nombre, clave, rol in USUARIOS:
        if not Usuario.query.filter_by(username=nombre).first():
            u = Usuario(username=nombre, rol=rol)
            u.set_password(clave)
            db.session.add(u)
    db.session.commit()


def asegurar_categorias():
    for n in CATEGORIAS:
        if not Categoria.query.filter_by(nombre=n).first():
            db.session.add(Categoria(nombre=n))
    db.session.commit()


def simular_movimientos(p, admin_id, rnd, objetivo):
    """Crea un historial coherente (nunca negativo) de ~60 días.
    `objetivo`: 'normal', 'bajo' o 'agotado' según el stock final deseado."""
    ahora = datetime.now()
    movs = []
    stock = rnd.randint(60, 160)
    movs.append(("entrada", stock, "Inventario inicial", ahora - timedelta(days=61)))
    for d in sorted(rnd.sample(range(2, 60), rnd.randint(6, 14)), reverse=True):
        fecha = ahora - timedelta(days=d, hours=rnd.randint(0, 8), minutes=rnd.randint(0, 59))
        if rnd.random() < 0.65 and stock > 1:
            q = rnd.randint(1, max(1, min(stock, 25)))
            stock -= q
            movs.append(("salida", q, rnd.choice(OBS_SALIDA), fecha))
        else:
            q = rnd.randint(10, 50)
            stock += q
            movs.append(("entrada", q, rnd.choice(OBS_ENTRADA), fecha))
    minimo = p.stock_minimo
    meta = {"agotado": 0, "bajo": rnd.randint(1, minimo)}.get(objetivo)
    ayer = ahora - timedelta(days=1)
    if meta is not None and stock > meta:
        movs.append(("salida", stock - meta, "Venta mostrador", ayer))
        stock = meta
    elif meta is None and stock <= minimo:
        q = minimo + rnd.randint(5, 30) - stock
        movs.append(("entrada", q, "Reposición de inventario", ayer))
        stock += q
    p.cantidad = stock
    for tipo, q, obs, fecha in movs:
        db.session.add(Movimiento(producto=p, usuario_id=admin_id, tipo=tipo,
                                  cantidad=q, observacion=obs, fecha=fecha))


def poblar():
    rnd = random.Random(2026)  # semilla fija: datos reproducibles
    asegurar_usuarios()
    asegurar_categorias()
    admin = Usuario.query.filter_by(username="admin").first()
    nuevos = 0
    for i, (nombre, sku, cat, precio, minimo, desc) in enumerate(PRODUCTOS):
        if Producto.query.filter_by(sku=sku).first():
            continue
        c = Categoria.query.filter_by(nombre=cat).first()
        p = Producto(nombre=nombre, sku=sku, descripcion=desc, precio=precio, stock_minimo=minimo,
                     categoria_id=c.id, cantidad=0, created_at=datetime.now() - timedelta(days=62))
        db.session.add(p)
        objetivo = "agotado" if i % 11 == 7 else "bajo" if i % 5 == 2 else "normal"
        simular_movimientos(p, admin.id, rnd, objetivo)
        nuevos += 1
    db.session.commit()
    return nuevos


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Puebla la BD con datos de ejemplo.")
    ap.add_argument("--reset", action="store_true", help="borra todos los datos antes de poblar")
    args = ap.parse_args()
    app = create_app()
    with app.app_context():
        if args.reset:
            db.drop_all()
            db.create_all()
        n = poblar()
        bajos = Producto.query.filter(Producto.cantidad <= Producto.stock_minimo).count()
        print("Productos nuevos: %d | Total productos: %d | Categorías: %d | Movimientos: %d | Con stock bajo: %d"
              % (n, Producto.query.count(), Categoria.query.count(), Movimiento.query.count(), bajos))
        print("Usuarios: admin/admin123 y cliente/cliente123")
