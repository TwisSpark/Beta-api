from flask import Flask, request, jsonify
import json
import os
from uuid import uuid4

app = Flask(__name__)

ARCHIVO = 'inv.json'

def cargar_datos():
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_datos(data):
    with open(ARCHIVO, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/inventario', methods=['POST'])
def inventario():
    input_data = request.get_json()

    # Validación base
    if not all(k in input_data for k in ['type', 'botID', 'userID']):
        return jsonify({
            'status': 'error',
            'message': 'Faltan parámetros obligatorios'
        }), 400

    type_op = input_data['type']
    bot_id = input_data['botID']
    user_id = input_data['userID']

    data = cargar_datos()
    if bot_id not in data:
        data[bot_id] = {}
    if user_id not in data[bot_id]:
        data[bot_id][user_id] = []

    # ============================================================
    # 🟢 ADD — Agregar item
    # ============================================================
    if type_op == 'add':
        if 'objeto' not in input_data or 'description' not in input_data:
            return jsonify({'status': 'error', 'message': 'Faltan objeto o description'}), 400

        objeto = input_data['objeto']
        descripcion = input_data['description']
        cantidad = max(1, int(input_data.get('cantidad', 1)))
        rareza = input_data.get('rareza', 'común')
        precio = float(input_data.get('precio', 0))
        emoji = input_data.get('emoji', '📦')
        categoria = input_data.get('categoria', 'general')

        encontrado = False

        for item in data[bot_id][user_id]:
            if item['objeto'] == objeto:
                item['cantidad'] += cantidad
                item['rareza'] = input_data.get('rareza', item['rareza'])
                item['precio'] = input_data.get('precio', item['precio'])
                item['emoji'] = input_data.get('emoji', item['emoji'])
                item['description'] = input_data.get('description', item['description'])
                item['categoria'] = categoria
                encontrado = True
                break

        if not encontrado:
            data[bot_id][user_id].append({
                'objeto': objeto,
                'description': descripcion,
                'id': str(uuid4()),
                'cantidad': cantidad,
                'rareza': rareza,
                'precio': precio,
                'emoji': emoji,
                'categoria': categoria
            })

        guardar_datos(data)

        return jsonify({
            'status': 'success',
            'message': 'Cantidad actualizada' if encontrado else 'Objeto agregado',
            'objeto': objeto,
            'cantidad': cantidad,
            'categoria': categoria
        })

    # ============================================================
    # 🟡 GET — Obtener inventario
    # ============================================================
    elif type_op == 'get':

        inventario = data.get(bot_id, {}).get(user_id, [])

        # ------------------------------------------------------------
        # 🔸 FORMATO 1 — LISTA SIMPLE
        # ------------------------------------------------------------
        if input_data.get('format') == 'lista':
            if not inventario:
                return jsonify({
                    'status': 'error',
                    'message': 'El usuario no tiene objetos'
                }), 404

            lista_formato = [
                f"{item.get('emoji', '📦')} {item['objeto']} (×{item['cantidad']})"
                for item in inventario
            ]

            return jsonify({
                'status': 'success',
                'message': 'Inventario formateado',
                'lista': lista_formato
            })

        # ------------------------------------------------------------
        # 🔸 FORMATO 2 — TODAS LAS CATEGORÍAS
        # ------------------------------------------------------------
        if input_data.get('format') == 'categoria' and 'categoria' not in input_data:
            if not inventario:
                return jsonify({
                    'status': 'error',
                    'message': 'El usuario no tiene objetos'
                }), 404

            categorias = {}
            for item in inventario:
                cat = item.get('categoria', 'general')
                if cat not in categorias:
                    categorias[cat] = []
                categorias[cat].append(
                    f"{item.get('emoji', '📦')} {item['objeto']} (×{item['cantidad']})"
                )

            return jsonify({
                'status': 'success',
                'message': 'Inventario agrupado por categorías',
                'categorias': categorias
            })

        # ------------------------------------------------------------
        # 🔸 FORMATO 3 — CATEGORÍA ESPECÍFICA
        # ------------------------------------------------------------
        if input_data.get('format') == 'categoria' and 'categoria' in input_data:

            categoria_buscada = input_data['categoria']

            filtrados = [
                f"{item.get('emoji', '📦')} {item['objeto']} (×{item['cantidad']})"
                for item in inventario
                if item.get('categoria', 'general') == categoria_buscada
            ]

            if not filtrados:
                return jsonify({
                    'status': 'error',
                    'message': f'No hay objetos en la categoría "{categoria_buscada}"'
                }), 404

            return jsonify({
                'status': 'success',
                'message': f'Objetos en la categoría "{categoria_buscada}"',
                'lista': filtrados
            })

        # ------------------------------------------------------------
        # 🔎 GET normal para un objeto
        # ------------------------------------------------------------
        if 'objeto' not in input_data:
            return jsonify({'status': 'error', 'message': 'Falta el campo objeto'}), 400

        objeto = input_data['objeto']

        if objeto == 'all':
            return jsonify({
                'status': 'success',
                'inventario': inventario
            })

        encontrados = [i for i in inventario if i['objeto'] == objeto]

        if not encontrados:
            return jsonify({'status': 'error', 'message': 'Objeto no encontrado'}), 404

        return jsonify({
            'status': 'success',
            'resultados': encontrados
        })

    # ============================================================
    # 🔴 DELETE — Borrar item
    # ============================================================
    elif type_op == 'delete':
        if 'objeto' not in input_data:
            return jsonify({'status': 'error', 'message': 'Falta objeto'}), 400

        objeto = input_data['objeto']
        id_obj = input_data.get('id')
        cantidad = int(input_data.get('cantidad', 0)) if 'cantidad' in input_data else None
        inventario = data[bot_id][user_id]

        for i, item in enumerate(inventario):
            if item['objeto'] == objeto and (not id_obj or item['id'] == id_obj):

                if cantidad:
                    item['cantidad'] -= cantidad
                    if item['cantidad'] <= 0:
                        inventario.pop(i)
                        guardar_datos(data)
                        return jsonify({
                            'status': 'success',
                            'message': 'Objeto eliminado (cantidad llegó a cero)'
                        })
                    guardar_datos(data)
                    return jsonify({
                        'status': 'success',
                        'message': 'Cantidad reducida'
                    })

                inventario.pop(i)
                guardar_datos(data)
                return jsonify({'status': 'success', 'message': 'Objeto eliminado'})

        return jsonify({'status': 'error', 'message': 'Objeto no encontrado'}), 404

    # ============================================================
    # 🧼 CLEAR — Borrar todo
    # ============================================================
    elif type_op == 'clear':
        inventario = data[bot_id][user_id]
        count = len(inventario)
        data[bot_id][user_id] = []
        guardar_datos(data)

        return jsonify({
            'status': 'success',
            'message': f'Se eliminó el inventario completo ({count} objetos)'
        })

    # ============================================================
    # ❗ Tipo desconocido
    # ============================================================
    else:
        return jsonify({'status': 'error', 'message': 'Tipo de operación inválido'}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)