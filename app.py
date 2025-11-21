from flask import Flask, request, jsonify, render_template
import json
import os
from uuid import uuid4

app = Flask(__name__)

# Ruta correcta del archivo
ARCHIVO = os.path.join('static', 'json', 'global', 'inv.json')

os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)

if not os.path.exists(ARCHIVO):
    with open(ARCHIVO, 'w', encoding='utf-8') as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

# ============================
#   FUNCIONES DE ARCHIVO
# ============================

def cargar_datos():
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def guardar_datos(data):
    with open(ARCHIVO, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================
#   FORMATO DE NÚMEROS
# ============================

def clean_int(value):
    """Permite: 20,000  — y convierte a: 20000"""
    if isinstance(value, int):
        return value

    value = str(value).replace(",", "")
    return int(value) if value.isdigit() else 0


def format_number(n):
    """Convierte 20000 → 20,000"""
    return f"{int(n):,}"


# ============================
# HOME
# ============================

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "API funcionando"})

# ============================
# RUTA /inventario
# ============================

@app.route('/inventario', methods=['POST'])
def inventario():
    input_data = request.get_json()

    if not input_data:
        return jsonify({"status": "error", "message": "JSON vacío o inválido"}), 400

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

    # ============================================
    # ADD
    # ============================================
    if type_op == 'add':

        if 'objeto' not in input_data or 'description' not in input_data:
            return jsonify({'status': 'error', 'message': 'Faltan objeto o description'}), 400

        objeto = input_data['objeto']
        descripcion = input_data['description']
        cantidad = max(1, clean_int(input_data.get('cantidad', 1)))
        rareza = input_data.get('rareza', 'común')
        precio = clean_int(input_data.get('precio', 0))
        emoji = input_data.get('emoji', '📦')
        categoria = input_data.get('categoria', 'general')

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
            'description': descripcion,
            'cantidad': format_number(cantidad),
            'rareza': rareza,
            'precio': format_number(precio),
            'emoji': emoji,
            'categoria': categoria
        })

    # ============================================
    # GET
    # ============================================
    elif type_op == 'get':

        # inventario vacío
        if not inventario:
            return jsonify({
                'status': 'success',
                'message': 'Nada por aquí… solo Sparkify, la futura reina del reino',
                'inventario': []
            })

        # formato lista
        if input_data.get('format') == 'lista':
            lista = [
                f"{i.get('emoji', '📦')} {i['objeto']} (×{format_number(i['cantidad'])})"
                for i in inventario
            ]
            return jsonify({
                'status': 'success',
                'inventario': lista
            })

        # formato categorias
        if input_data.get('format') == 'categoria':
            categorias = {}
            for i in inventario:
                cat = i.get('categoria', 'general')
                categorias.setdefault(cat, []).append(
                    f"{i.get('emoji','📦')} {i['objeto']} (×{format_number(i['cantidad'])})"
                )
            return jsonify({
                'status': 'success',
                'categorias': categorias,
                'total_categorias': len(categorias)
            })

        # buscar objeto exacto
        if 'objeto' in input_data:
            objeto = input_data['objeto']
            if objeto == 'all':
                return jsonify({'status': 'success', 'inventario': inventario})

            encontrados = [i for i in inventario if i['objeto'] == objeto]
            if not encontrados:
                return jsonify({'status': 'error', 'message': 'Objeto no encontrado'})

            return jsonify({'status': 'success', 'resultados': encontrados})

        # GET normal
        return jsonify({'status': 'success', 'inventario': inventario})

    # ============================================
    # DELETE
    # ============================================
    elif type_op == 'delete':

        if 'objeto' not in input_data:
            return jsonify({'status': 'error', 'message': 'Falta objeto'}), 400

        objeto = input_data['objeto']
        cantidad = clean_int(input_data.get('cantidad', 0)) if 'cantidad' in input_data else None

        for i, item in enumerate(inventario):
            if item['objeto'] == objeto:
                if cantidad:
                    item['cantidad'] -= cantidad
                    if item['cantidad'] <= 0:
                        inventario.pop(i)
                        guardar_datos(data)
                        return jsonify({'status': 'success', 'message': 'Objeto eliminado (cantidad llegó a cero)'})
                    guardar_datos(data)
                    return jsonify({'status': 'success', 'message': 'Cantidad reducida'})

                inventario.pop(i)
                guardar_datos(data)
                return jsonify({'status': 'success', 'message': 'Objeto eliminado'})

        return jsonify({'status': 'error', 'message': 'Objeto no encontrado'}), 404

    # ============================================
    # CLEAR
    # ============================================
    elif type_op == 'clear':
        count = len(inventario)
        data[bot_id][user_id] = []
        guardar_datos(data)
        return jsonify({'status': 'success', 'message': f'Se eliminó el inventario completo ({count} objetos)'})

    # ============================================
    # ERROR
    # ============================================
    else:
        return jsonify({'status': 'error', 'message': 'Tipo de operación inválido'}), 400


# ============================
# RUTAS HTML
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
# EXEC
# ============================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)