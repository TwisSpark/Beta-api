from flask import Flask, request, jsonify, render_template
import json
import os
from uuid import uuid4

app = Flask(__name__)

# Ruta correcta del archivo JSON
ARCHIVO = os.path.join('static', 'json', 'global', 'inv.json')

# Crear carpetas si no existen
os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)

# Crear archivo si no existe
if not os.path.exists(ARCHIVO):
    with open(ARCHIVO, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

# ============================
#   FUNCIONES AUXILIARES
# ============================

def normalizar_inventario(inventario):
    """Asegura que las cantidades sean enteros reales (evita notación científica)."""
    for item in inventario:
        try:
            item["cantidad"] = int(item.get("cantidad", 1))
        except:
            item["cantidad"] = 1


def cargar_datos():
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except:
                return {}

            # 🔥 Normalizar cantidades en todo el inventario
            for bot in data.values():
                for user in bot.values():
                    normalizar_inventario(user)

            return data
    return {}


def guardar_datos(data):
    # Normalizar todas las cantidades antes de guardar
    for bot in data.values():
        for user in bot.values():
            normalizar_inventario(user)

    with open(ARCHIVO, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================
#   RUTA DE PRUEBA
# ============================

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "API funcionando"})


# ============================
#   RUTA PRINCIPAL /inventario
# ============================

@app.route('/inventario', methods=['POST'])
def inventario():
    input_data = request.get_json()
    if not input_data:
        return jsonify({"status": "error", "message": "JSON vacío o inválido"}), 400

    # Campos obligatorios
    if not all(k in input_data for k in ['type', 'botID', 'userID']):
        return jsonify({'status': 'error', 'message': 'Faltan parámetros obligatorios'}), 400

    type_op = input_data['type']
    bot_id = input_data['botID']
    user_id = input_data['userID']

    data = cargar_datos()
    if bot_id not in data:
        data[bot_id] = {}
    if user_id not in data[bot_id]:
        data[bot_id][user_id] = []

    inventario = data[bot_id][user_id]
    normalizar_inventario(inventario)

    # ============================================================
    # 🟢 ADD — Agregar item
    # ============================================================
    if type_op == 'add':
        if 'objeto' not in input_data or 'description' not in input_data:
            return jsonify({'status': 'error', 'message': 'Faltan objeto o description'}), 400

        objeto = input_data['objeto']
        descripcion = input_data['description']

        # Siempre entero real
        try:
            cantidad = int(input_data.get('cantidad', 1))
        except:
            cantidad = 1

        cantidad = max(1, cantidad)

        rareza = input_data.get('rareza', 'común')
        emoji = input_data.get('emoji', '📦')
        categoria = input_data.get('categoria', 'general')

        # Siempre float normal
        try:
            precio = float(input_data.get('precio', 0))
        except:
            precio = 0.0

        encontrado = False
        for item in inventario:
            if item['objeto'] == objeto:
                item['cantidad'] += cantidad
                item['rareza'] = rareza
                item['precio'] = precio
                item['emoji'] = emoji
                item['description'] = descripcion
                item['categoria'] = categoria
                encontrado = True
                break

        if not encontrado:
            inventario.append({
                'id': str(uuid4()),
                'objeto': objeto,
                'description': descripcion,
                'cantidad': cantidad,
                'rareza': rareza,
                'precio': precio,
                'emoji': emoji,
                'categoria': categoria
            })

        guardar_datos(data)

        return jsonify({
            'status': 'success',
            'message': 'Objeto agregado' if not encontrado else 'Cantidad actualizada',
            'objeto': objeto,
            'cantidad': cantidad,
            'categoria': categoria,
            'total_items': sum(i['cantidad'] for i in inventario)
        })

    # ============================================================
    # 🟡 GET — Obtener inventario
    # ============================================================
    elif type_op == 'get':
        if not inventario:
            return jsonify({
                'status': 'success',
                'message': 'Nada por aquí… solo Sparkify, la futura reina del reino',
                'inventario': []
            })

        # Formato lista
        if input_data.get('format') == 'lista':
            lista = [
                f"{i.get('emoji', '📦')} {i['objeto']} (×{i['cantidad']})"
                for i in inventario
            ]
            return jsonify({
                'status': 'success',
                'total_items': sum(i['cantidad'] for i in inventario),
                'inventario': lista
            })

        # Formato categoría
        if input_data.get('format') == 'categoria':
            categorias = {}
            for i in inventario:
                cat = i.get('categoria', 'general')
                categorias.setdefault(cat, []).append(
                    f"{i.get('emoji', '📦')} {i['objeto']} (×{i['cantidad']})"
                )
            return jsonify({
                'status': 'success',
                'categorias': categorias,
                'total_categorias': len(categorias)
            })

        # Buscar objeto específico
        if 'objeto' in input_data:
            objeto = input_data['objeto']
            if objeto == 'all':
                return jsonify({'status': 'success', 'inventario': inventario})

            encontrados = [i for i in inventario if i['objeto'] == objeto]
            if not encontrados:
                return jsonify({'status': 'error', 'message': 'Objeto no encontrado'})

            return jsonify({'status': 'success', 'resultados': encontrados})

        return jsonify({'status': 'success', 'inventario': inventario})

    # ============================================================
    # 🔴 DELETE — Borrar item
    # ============================================================
    elif type_op == 'delete':
        if 'objeto' not in input_data:
            return jsonify({'status': 'error', 'message': 'Falta objeto'}), 400

        objeto = input_data['objeto']

        try:
            cantidad = int(input_data.get('cantidad', 0))
        except:
            cantidad = 1

        for i, item in enumerate(inventario):
            if item['objeto'] == objeto:
                if cantidad > 0:
                    item['cantidad'] -= cantidad
                    if item['cantidad'] <= 0:
                        inventario.pop(i)
                        guardar_datos(data)
                        return jsonify({'status': 'success', 'message': 'Objeto eliminado'})
                    guardar_datos(data)
                    return jsonify({'status': 'success', 'message': 'Cantidad reducida'})

                # Eliminar sin cantidad
                inventario.pop(i)
                guardar_datos(data)
                return jsonify({'status': 'success', 'message': 'Objeto eliminado'})

        return jsonify({'status': 'error', 'message': 'Objeto no encontrado'}), 404

    # ============================================================
    # 🧼 CLEAR — Borrar todo
    # ============================================================
    elif type_op == 'clear':
        count = len(inventario)
        data[bot_id][user_id] = []
        guardar_datos(data)
        return jsonify({
            'status': 'success',
            'message': f'Se eliminó el inventario completo ({count} objetos)'
        })

    else:
        return jsonify({'status': 'error', 'message': 'Tipo de operación inválido'}), 400


# ============================
#   RUTAS HTML
# ============================

@app.route('/rutas')
def ver_rutas():
    rutas = []
    for rule in app.url_map.iter_rules():
        rutas.append({
            'ruta': str(rule),
            'metodos': ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        })
    return render_template('global/rutas.html', rutas=rutas)


# ============================
#   EJECUTAR SERVIDOR
# ============================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)