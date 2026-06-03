# Triển khai MTL Validator vào Dify Agent

## 1. Deploy API ra public

Dify cloud (dyfi.besen.vn) cần URL public để gọi API. Chọn 1 cách:

### Cách A: ngrok (test nhanh, miễn phí)

```powershell
# Tải ngrok từ https://ngrok.com và cài
ngrok http 8000
# → Copy URL dạng https://xxxx.ngrok-free.app
```

### Cách B: Docker + Cloud VPS (production)

```bash
# Build
docker build -t mtl-validator .

# Run
docker run -d -p 8000:8000 --name mtl-validator mtl-validator

# Mở port 8000 trên firewall, trỏ domain nếu có
```

### Cách C: Railway / Render / Fly.io (free tier)

Push code lên GitHub → deploy tự động qua Railway/Render với Dockerfile có sẵn.

---

## 2. Đăng ký Tool trong Dify

Vào Dify → **Tools** → **Create Custom Tool** → chọn **OpenAPI / Swagger**

### Nhập URL OpenAPI spec:

```
https://your-server.com/dify/openapi.json
```

Hoặc paste nội dung file `openapi.yaml` vào tab **Import from URL / Paste**.

### Kiểm tra Tool đã import đúng:

Sau khi import, Dify sẽ hiện:
- **POST /api/v1/validate** — tool chính để validate file
- **GET /api/v1/health** — tool kiểm tra service

---

## 3. Tạo Dify Agent Workflow

Vào Dify → **Studio** → **Create from blank** → chọn **Agent / Chatflow**

### Cấu hình Agent:

**System Prompt:**
```
Bạn là trợ lý kiểm tra file MTL (Master Timeline) cho phòng điều hành dự án.
Nhiệm vụ của bạn:
1. Khi nhân viên gửi file .xlsx, gọi tool `validateFile` để kiểm tra.
2. Đọc kết quả từ `messages.user_message` và gửi lại chính xác text đó cho nhân viên.
3. Dựa vào `messages.status_hint`:
   - BLOCKED → yêu cầu nhân viên sửa GẤP các lỗi CRITICAL và nộp lại ngay
   - FAIL_NEED_FIX → yêu cầu sửa lỗi ERROR trước khi nộp lại
   - PASS_WITH_NOTES → thông báo đạt, nhắc nhẹ các lưu ý nếu có
   - PASS_CLEAN → khen ngợi, file hoàn hảo!
4. KHÔNG tự ý thay đổi nội dung user_message — đó là text đã được format sẵn cho nhân viên.

File đạt chuẩn khi KHÔNG có lỗi CRITICAL hoặc ERROR.
WARNING có thể bỏ qua nếu là ghi chú thủ công.
```

### User Prompt Template:
```
Người dùng gửi file: {{file}}
Nhân viên: {{employee_id}}
---
Hãy kiểm tra file này và thông báo kết quả cho nhân viên.
```

### Bắt buộc bật:
- **File Upload** — cho phép người dùng gửi file .xlsx
- **Tool: validateFile** — gắn vào workflow

---

## 4. Test thử

Vào Dify → **Preview / Debug**:

1. Upload file test (VD: PT10A có lỗi thiếu tên công ty)
2. Gửi tin nhắn
3. Kiểm tra response — Agent phải gọi tool, đọc `user_message`, và trả lời nhân viên

**Response mong đợi:**
```
LOI COVER:
  [CRITICAL] Cover thiếu tên công ty
  [WARNING] Cover thiếu yêu cầu chung

File `...` cần sửa 1 lỗi:
Vui long sua cac loi tren va gui lai file.
```

---

## 5. Kịch bản thực tế

### Nhân viên nộp file mới mỗi ngày:
```
Nhân viên: "Đây ạ" [gửi file MTL_PhuocThien_20260528.xlsx]

Agent: gọi validateFile → kết quả PASS_WITH_NOTES
Agent: "File đạt chuẩn ạ. Có 1 lưu ý nhỏ: [WARNING] Cover thiếu yêu cầu chung — nếu không có thì bỏ qua."
```

### Nhân viên nộp file lỗi:
```
Nhân viên: "Đây ạ" [gửi file MTL_PhuocThien_10A.xlsx]

Agent: gọi validateFile → kết quả BLOCKED
Agent: "File của anh/chị bị lỗi NGHIÊM TRỌNG:
  [CRITICAL] Cover thiếu tên công ty
  => Cách sửa: Điền tên công ty vào Cover (VD: 'Công ty TNHH...')
Vui lòng sửa và gửi lại ạ."
```

---

## 6. Endpoint tham khảo

| Endpoint | Method | Dùng cho |
|---|---|---|
| `/` | GET | Test UI (kéo thả upload) |
| `/api/v1/validate` | POST | Dify Agent gọi |
| `/api/v1/health` | GET | Dify kiểm tra tool còn sống |
| `/dify/openapi.json` | GET | Dify import tool (JSON) |
| `/dify/openapi.yaml` | GET | Dify import tool (YAML) |
| `/docs` | GET | FastAPI auto-docs |
| `/api-docs` | GET | Swagger UI (spec đầy đủ, tiếng Việt) |

---

## 7. Troubleshooting

| Vấn đề | Nguyên nhân | Cách sửa |
|---|---|---|
| Dify không import được tool | URL OpenAPI không public | Dùng ngrok hoặc deploy lên server public |
| File upload báo lỗi | File > 15MB | Tăng `max_upload_size` trong Dify config |
| Agent không gọi tool | Chưa gắn tool vào Agent | Vào Agent settings → Tools → thêm validateFile |
| Response tiếng Anh | System prompt chưa set tiếng Việt | Copy nguyên System Prompt ở trên |
