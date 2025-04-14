import os
import pandas as pd
from flask import Flask, request, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename
from zipfile import ZipFile

app = Flask(__name__)

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

    numeracion = {}
    zip_name = "autofacturas.zip"

    with ZipFile(zip_name, 'w') as zipf:
        for _, row in merged.iterrows():
            cliente = row["Cliente"]
            numeracion[cliente] = numeracion.get(cliente, 0) + 1
            num_factura = f"{cliente[:2].upper()}{numeracion[cliente]:03d}"
            pdf_filename = f"{cliente}_{num_factura}.pdf".replace(" ", "_")

            c = canvas.Canvas(pdf_filename, pagesize=A4)
            c.setFont("Helvetica", 12)
            y = 800
            c.drawString(50, y, "Autofactura")
            y -= 30
            c.drawString(50, y, f"Cliente: {cliente}")
            y -= 20
            c.drawString(50, y, f"NIF: {row['NIF']}")
            y -= 20
            c.drawString(50, y, f"Dirección: {row['Dirección']}")
            y -= 20
            c.drawString(50, y, f"Fecha: {row['Fecha']}")
            y -= 20
            c.drawString(50, y, f"Número de factura: {num_factura}")
            y -= 20
            c.drawString(50, y, f"Concepto: {row['Concepto']}")
            y -= 20
            c.drawString(50, y, f"Importe: {row['Importe']:.2f} €")
            c.save()

            zipf.write(pdf_filename)
            os.remove(pdf_filename)

    os.remove(clientes_path)
    os.remove(facturas_path)

    return send_file(zip_name, as_attachment=True)

# Escuchar en el puerto que Render especifica
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)