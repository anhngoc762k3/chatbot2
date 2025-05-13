import asyncio
import platform
import os
from flask import Flask, request, jsonify, render_template
from g4f.client import Client
import pdfplumber

# Khởi tạo asyncio phù hợp với Windows
if platform.system() == "Windows":
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

client = Client()
app = Flask(__name__)

# Tạo thư mục upload nếu chưa có
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Đọc PDF
def read_pdf(file_path):
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        return f"Lỗi khi đọc file PDF: {str(e)}"

# Đọc file mặc định khi khởi động
pdf_file_path = "D1.pdf"
default_pdf_text = read_pdf(pdf_file_path)

# Tạo phản hồi từ chatbot
def generate_response(question, combined_text):
    try:
        context = combined_text[:6000] if len(combined_text) > 6000 else combined_text
        prompt = f"Đây là nội dung tài liệu:\n{context}\n\nCâu hỏi: {question}\nTrả lời:"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Lỗi khi tạo phản hồi: {str(e)}"

# Giao diện chính
@app.route("/")
def index():
    return render_template("index.html")

# API hỏi đáp
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    user_pdf_text = data.get("pdfText", "")

    combined_text = default_pdf_text + "\n" + user_pdf_text
    answer = generate_response(question, combined_text)
    return jsonify({"answer": answer})

# API upload file PDF
@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy tệp nào."})

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Tên file trống."})

    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        text = read_pdf(file_path)

        if not text.strip():
            return jsonify({"success": False, "message": "Không thể trích xuất nội dung từ file PDF."})

        return jsonify({"success": True, "text": text})
    except Exception as e:
        return jsonify({"success": False, "message": f"Lỗi xử lý file: {str(e)}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4000))
    app.run(host="0.0.0.0", port=port)
