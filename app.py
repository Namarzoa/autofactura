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

    clientes = pd.read_excel(clientes_path)
    facturas = pd.read_excel(facturas_path)
    merged = facturas.merge(clientes, on="CIE", how="left")

    template = env.get_template("plantilla.html")
    zip_name = "autofacturas.zip"
    numeracion = {}

    with ZipFile(zip_name, 'w') as zipf:
        for _, row in merged.iterrows():
            cliente = row["Cliente"]
            numeracion[cliente] = numeracion.get(cliente, 0) + 1
            numero_factura = f"{cliente[:2].upper()}{numeracion[cliente]:03d}"

            html = template.render(
                numero_factura=numero_factura,
                proveedor_nombre=cliente,
                proveedor_cif=row["NIF"],
                proveedor_direccion=row["Dirección"],
                fecha=str(row["Fecha"]),
                items=[{
                    'descripcion': row["Concepto"],
                    'unidades': 1,
                    'precio_unitario': f"{row['Importe']:.2f}",
                    'iva': "21",
                    'total': f"{row['Importe'] * 1.21:.2f}"
                }],
                subtotal=f"{row['Importe']:.2f}",
                total_iva=f"{row['Importe'] * 0.21:.2f}",
                total=f"{row['Importe'] * 1.21:.2f}",
                iban="ES00 1234 5678 9012 3456 7890"
            )

            pdf_path = f"{cliente}_{numero_factura}.pdf".replace(" ", "_")
            pdfkit.from_string(html, pdf_path)
            zipf.write(pdf_path)
            os.remove(pdf_path)

    os.remove(clientes_path)
    os.remove(facturas_path)
    return send_file(zip_name, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)