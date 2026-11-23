"""Puebla la base de datos con datos de ejemplo.

Uso:
    python seed_datos.py            # agrega los datos que falten (no duplica)
    python seed_datos.py --reset    # BORRA todo y vuelve a crear los datos
"""
import argparse
import os
import random
from datetime import date, datetime, timedelta

from flask_migrate import upgrade

from app import create_app, db
from app.cli import sembrar_base
from app.models import Categoria, Lote, Movimiento, Producto, Proveedor, Usuario

CATEGORIAS = ["General", "Electrónica", "Papelería", "Hogar", "Herramientas", "Aseo", "Alimentos"]

# (nombre, nit, contacto, teléfono, correo, dirección, lead_time_dias)
PROVEEDORES = [
    ("Distribuidora Andina", "900123456-1", "Laura Pérez", "3001234567", "compras@andina.co", "Bogotá", 3),
    ("TecnoSuministros SAS", "901234567-2", "Carlos Gómez", "3102345678", "ventas@tecnosum.co", "Medellín", 5),
    ("Papelería Central", "900345678-3", "Ana Rodríguez", "3203456789", "pedidos@papeleriacentral.co", "Cali", 2),
    ("Hogar y Aseo Ltda", "901456789-4", "Jorge Díaz", "3154567890", "contacto@hogaryaseo.co", "Barranquilla", 4),
    ("Alimentos del Campo", "900567890-5", "María Torres", "3185678901", "compras@alimentoscampo.co", "Pereira", 6),
]

CATEGORIA_PROVEEDOR = {
    "General": "Distribuidora Andina",
    "Electrónica": "TecnoSuministros SAS",
    "Herramientas": "TecnoSuministros SAS",
    "Papelería": "Papelería Central",
    "Hogar": "Hogar y Aseo Ltda",
    "Aseo": "Hogar y Aseo Ltda",
    "Alimentos": "Alimentos del Campo",
}

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


def asegurar_categorias():
    for n in CATEGORIAS:
        if not Categoria.query.filter_by(nombre=n).first():
            db.session.add(Categoria(nombre=n))
    db.session.commit()


def _motivo(observacion, tipo):
    texto = (observacion or "").lower()
    if "dañado" in texto or "danado" in texto:
        return "dano"
    if "devolución" in texto or "devolucion" in texto:
        return "devolucion"
    if "ajuste" in texto:
        return "diferencia_conteo"
    return "compra" if tipo == "entrada" else "venta"


def simular_movimientos(p, admin_id, rnd, objetivo, indice=0):
    """Crea un historial coherente (nunca negativo) de ~60 días.
    `objetivo`: 'normal', 'bajo' o 'agotado' según el stock final deseado."""
    ahora = datetime.now()
    registros = []
    stock = rnd.randint(60, 160)

    def agregar(tipo, cantidad, observacion, fecha, antes, despues):
        motivo = _motivo(observacion, tipo)
        if motivo == "dano":
            tipo = "merma"
        elif motivo == "diferencia_conteo":
            tipo = "ajuste"
        registros.append({
            "tipo": tipo,
            "cantidad": cantidad,
            "observacion": observacion,
            "fecha": fecha,
            "stock_anterior": antes,
            "stock_nuevo": despues,
            "delta": despues - antes,
            "motivo": motivo,
        })

    agregar("entrada", stock, "Inventario inicial", ahora - timedelta(days=61), 0, stock)

    for d in sorted(rnd.sample(range(2, 60), rnd.randint(6, 14)), reverse=True):
        fecha = ahora - timedelta(days=d, hours=rnd.randint(0, 8), minutes=rnd.randint(0, 59))
        if rnd.random() < 0.65 and stock > 1:
            cantidad = rnd.randint(1, max(1, min(stock, 25)))
            antes = stock
            stock -= cantidad
            agregar("salida", cantidad, rnd.choice(OBS_SALIDA), fecha, antes, stock)
        else:
            cantidad = rnd.randint(10, 50)
            antes = stock
            stock += cantidad
            agregar("entrada", cantidad, rnd.choice(OBS_ENTRADA), fecha, antes, stock)

    minimo = p.stock_minimo
    meta = {"agotado": 0, "bajo": rnd.randint(1, minimo)}.get(objetivo)
    ayer = ahora - timedelta(days=1)

    if meta is not None and stock > meta:
        cantidad = stock - meta
        antes = stock
        stock = meta
        agregar("salida", cantidad, "Venta mostrador", ayer, antes, stock)
    elif meta is None and stock <= minimo:
        cantidad = minimo + rnd.randint(5, 30) - stock
        antes = stock
        stock += cantidad
        agregar("entrada", cantidad, "Reposición de inventario", ayer, antes, stock)

    p.cantidad = stock
    for registro in registros:
        db.session.add(Movimiento(
            producto=p,
            usuario_id=admin_id,
            costo_unitario=p.precio_compra,
            impacto=round(abs(registro["delta"]) * (p.precio_compra or 0), 2),
            **registro,
        ))

    # Lotes de demostración: reparten el stock final y generan alertas variadas.
    if stock > 0:
        if indice % 7 == 0:
            offsets = [-4, 25]
        elif indice % 5 == 0:
            offsets = [7]
        elif indice % 3 == 0:
            offsets = [35, 120]
        else:
            offsets = [90]
        cantidades = [stock] if len(offsets) == 1 else [max(1, stock // 2), stock - max(1, stock // 2)]
        for j, (dias, cantidad) in enumerate(zip(offsets, cantidades), start=1):
            if cantidad <= 0:
                continue
            db.session.add(Lote(
                producto=p,
                codigo="L-%02d" % j,
                fecha_vencimiento=date.today() + timedelta(days=dias),
                cantidad_inicial=cantidad,
                cantidad_actual=cantidad,
                costo_unitario=p.precio_compra,
            ))


def poblar():
    rnd = random.Random(2026)  # semilla fija: datos reproducibles
    sembrar_base()
    asegurar_categorias()

    proveedores = {}
    for nombre, nit, contacto, telefono, email, direccion, lead in PROVEEDORES:
        pr = Proveedor.query.filter_by(nombre=nombre).first()
        if not pr:
            pr = Proveedor(nombre=nombre, nit=nit, contacto=contacto, telefono=telefono,
                           email=email, direccion=direccion, lead_time_dias=lead)
            db.session.add(pr)
        proveedores[nombre] = pr
    db.session.flush()

    admin = Usuario.query.filter_by(username="admin").first()
    nuevos = 0
    for i, (nombre, sku, cat, precio, minimo, desc) in enumerate(PRODUCTOS):
        if Producto.query.filter_by(sku=sku).first():
            continue
        c = Categoria.query.filter_by(nombre=cat).first()
        p = Producto(
            nombre=nombre,
            sku=sku,
            codigo_barras="770%010d" % (i + 1),
            descripcion=desc,
            precio=precio,
            precio_compra=round(precio * 0.7, 2),
            stock_minimo=minimo,
            dias_alerta_vencimiento=15,
            activo=True,
            categoria_id=c.id,
            proveedor=proveedores.get(CATEGORIA_PROVEEDOR.get(cat)),
            cantidad=0,
            created_at=datetime.now() - timedelta(days=62),
        )
        db.session.add(p)
        objetivo = "agotado" if i % 11 == 7 else "bajo" if i % 5 == 2 else "normal"
        simular_movimientos(p, admin.id, rnd, objetivo, i)
        nuevos += 1
    db.session.commit()
    return nuevos


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Puebla la BD con datos de ejemplo.")
    ap.add_argument("--reset", action="store_true", help="borra todos los datos antes de poblar")
    args = ap.parse_args()

    if args.reset:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "inventario.db")
        if os.path.exists(db_path):
            os.remove(db_path)

    app = create_app()
    with app.app_context():
        # Garantiza que el esquema exista y esté actualizado (idempotente).
        upgrade()
        n = poblar()
        bajos = Producto.query.filter(Producto.cantidad <= Producto.stock_minimo).count()
        ajustes = Movimiento.query.filter_by(tipo="ajuste").count()
        mermas = Movimiento.query.filter_by(tipo="merma").count()
        print("Productos nuevos: %d | Total productos: %d | Categorías: %d | Proveedores: %d | Lotes: %d | Movimientos: %d (ajustes: %d, mermas: %d) | Con stock bajo: %d"
              % (n, Producto.query.count(), Categoria.query.count(), Proveedor.query.count(),
                 Lote.query.count(), Movimiento.query.count(), ajustes, mermas, bajos))
        print("Usuarios: admin/admin123 (tendero) y cliente/cliente123 (cajero)")
