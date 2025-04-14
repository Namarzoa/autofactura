import os
import pandas as pd
import pdfkit
from flask import Flask, request, send_file
from jinja2 import Environment, FileSystemLoader
from werkzeug.utils import secure_filename
from zipfile import ZipFile

app = Flask(__name__)
env = Environment(loader=FileSystemLoader("."))

@app.route('/')
def index():
    return open("index.html").read()

@app.route('/generate', methods=['POST'])
def generate():
    clientes_file = request.files['clientes']
    facturas_file = request.files['facturas']
    clientes_path = secure_filename(clientes_file.filename)
    facturas_path = secure_filename(facturas_file.filename)
    clientes_file.save(clientes_path)
    facturas_file.save(facturas_path)

    logo_absoluto = os.path.abspath("logo.png")
    clientes = pd.read_excel(clientes_path)
    facturas = pd.read_excel(facturas_path)

    clientes.set_index("CIF", inplace=True)
    template = env.get_template("plantilla.html")
    zip_name = "autofacturas.zip"

    options = {
        'enable-local-file-access': '',
        'encoding': 'UTF-8',
        'margin-top': '20mm',
        'margin-bottom': '20mm',
        'margin-left': '15mm',
        'margin-right': '15mm'
    }

    # Agrupar por cliente (CIF) y fecha
    grouped = facturas.groupby(['CIF', 'Fecha'])

    with ZipFile(zip_name, 'w') as zipf:
        for (cif, fecha), group in grouped:
            if cif not in clientes.index:
                continue

            cliente_info = clientes.loc[cif]
            proveedor_nombre = cliente_info["Cliente"]
            direccion = cliente_info["Dirección"]
            prefijo = cliente_info["Prefijo"]
            ultima = int(cliente_info["UltimaFactura"])
            iban = cliente_info["IBAN"]

            nueva_numeracion = ultima + 1
            numero_factura = f"{prefijo}{nueva_numeracion:03d}"

            items = []
            subtotal = 0
            for _, row in group.iterrows():
                importe = row["Importe"]
                subtotal += importe
                items.append({
                    'descripcion': row["Concepto"],
                    'unidades': 1,
                    'precio_unitario': f"{importe:.2f}",
                    'iva': "21",
                    'total': f"{importe * 1.21:.2f}"
                })

            total_iva = subtotal * 0.21
            total = subtotal * 1.21

            html = template.render(
                numero_factura=numero_factura,
                proveedor_nombre=proveedor_nombre,
                proveedor_cif=cif,
                proveedor_direccion=direccion,
                fecha=str(fecha),
                items=items,
                subtotal=f"{subtotal:.2f}",
                total_iva=f"{total_iva:.2f}",
                total=f"{total:.2f}",
                iban=iban,
                logo_path=logo_absoluto
            )

            pdf_path = f"{proveedor_nombre}_{numero_factura}.pdf".replace(" ", "_")
            pdfkit.from_string(html, pdf_path, options=options)
            zipf.write(pdf_path)
            os.remove(pdf_path)

            clientes.at[cif, "UltimaFactura"] = nueva_numeracion

    clientes.reset_index().to_excel(clientes_path, index=False)
    os.remove(facturas_path)

    return send_file(zip_name, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)