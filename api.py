from fastapi import File, UploadFile, FastAPI, HTTPException, Form, Path, Query, status, Request
import os, shutil, string, secrets, random, asyncio, logging, time
from typing import Literal, Optional, List, Annotated
from mysql.connector import Error
import db, uuid, json
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from datetime import date, datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
from decimal import Decimal
from fastapi.middleware.cors import CORSMiddleware
import traceback
import hmac
import hashlib, base64, requests

app = FastAPI()

UPLOAD_FOLDER = "uploads"

partner_code = "MOMOVMUO20250710"
access_key = "D0sYXqUpjtp1GQvp"
secret_key = "VmE6M950wN3BqmNc7RE6vKe2Fs4pyWLH"
endpoint = "https://payment.momo.vn/v2/gateway/api/create"
urlApp =  "https://related-burro-selected.ngrok-free.app"
redirect_url = f"{urlApp}/return"
ipn_url = f"{urlApp}/momo-ipn"

@app.get("/return")
async def momo_return(request: Request):
    result_code = request.query_params.get('resultCode')
    order_id = request.query_params.get('orderId')
    
    # Tạo HTML page với button quay lại app
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kết quả thanh toán</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="text-align: center; padding: 50px;">
        <h2>{'Thanh toán thành công!' if result_code == '0' else 'Thanh toán thất bại!'}</h2>
        <p>Mã đơn hàng: {order_id}</p>
        <button onclick="location.href='yourapp://payment/return?orderId={order_id}&resultCode={result_code}'" 
                style="padding: 15px 30px; font-size: 16px; background: #d82d8b; color: white; border: none; border-radius: 5px;">
            Quay lại App
        </button>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Middleware để handle ngrok headers
@app.middleware("http")
async def add_ngrok_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response

class PaymentRequest(BaseModel):
    so_tien: int
    phuong_thuc: str  # chỉ dùng "momo" ở đây
    ma_don_hang: int

# Cấu hình URLs đúng
NGROK_URL = "https://related-burro-selected.ngrok-free.app"
ipn_url = f"{NGROK_URL}/momo-ipn"

@app.post("/tao-url-thanh-toan")
def tao_url_thanh_toan(data: PaymentRequest):
    if data.phuong_thuc != "momo":
        return {"error": "Chỉ hỗ trợ momo trong ví dụ này"}
    
    # Tạo thông tin đơn hàng
    order_id = str(data.ma_don_hang)
    request_id = str(uuid.uuid4())
    amount = str(data.so_tien)
    order_info = "Thanh toán đơn hàng #" + order_id
    extra_data = ""
    request_type = "payWithMethod"  # Sửa từ "captureWallet" thành "payWithMethod"
    
    # Return URL trực tiếp về app
    return_url = f"pizzaapp://payment?orderId={order_id}"
    
    # Tạo chữ ký theo thứ tự alphabet
    raw_signature = (
        f"accessKey={access_key}&amount={amount}&extraData={extra_data}"
        f"&ipnUrl={ipn_url}&orderId={order_id}&orderInfo={order_info}"
        f"&partnerCode={partner_code}&redirectUrl={return_url}"
        f"&requestId={request_id}&requestType={request_type}"
    )
    
    signature = hmac.new(
        secret_key.encode(),
        raw_signature.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Payload gửi lên MoMo
    payload = {
        "partnerCode": partner_code,
        "partnerName": "Pizza App",
        "storeId": "PizzaStore01",
        "requestId": request_id,
        "amount": amount,
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": return_url,
        "ipnUrl": ipn_url,
        "lang": "vi",
        "extraData": extra_data,
        "requestType": request_type,
        "signature": signature
    }
    
    # Log debug
    print(f"=== MoMo Payment Request ===")
    print(f"Order ID: {order_id}")
    print(f"Amount: {amount}")
    print(f"Return URL: {return_url}")
    print(f"IPN URL: {ipn_url}")
    print(f"Raw Signature: {raw_signature}")
    print(f"Signature: {signature}")
    print(f"Payload: {payload}")
    
    # Gửi request đến MoMo
    try:
        response = requests.post(
            endpoint, 
            json=payload, 
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; Pizza App/1.0)'
            },
            timeout=30
        )
        
        result = response.json()
        
        print(f"=== MoMo Response ===")
        print(f"Status Code: {response.status_code}")
        print(f"Result: {result}")
        
        if result.get("resultCode") == 0:
            return {
                "success": True,
                "payUrl": result.get("payUrl"),
                "deeplink": result.get("deeplink"),
                "qrCodeUrl": result.get("qrCodeUrl"),
                "message": result.get("message"),
                "resultCode": result.get("resultCode"),
                "orderId": order_id,
                "returnUrl": return_url
            }
        else:
            return {
                "success": False,
                "error": result.get("message", "Lỗi không xác định"),
                "resultCode": result.get("resultCode", -1),
                "orderId": order_id
            }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout khi gọi API MoMo",
            "resultCode": -1
        }
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return {
            "success": False,
            "error": f"Lỗi kết nối API MoMo: {str(e)}",
            "resultCode": -1
        }
    except Exception as e:
        print(f"Error calling MoMo API: {e}")
        return {
            "success": False,
            "error": f"Lỗi khi gọi API MoMo: {str(e)}",
            "resultCode": -1
        }

# API xử lý payment callback từ app (optional)
@app.get("/payment-callback")
def payment_callback(
    orderId: str,
    resultCode: str = "0",
    message: str = "",
    transId: str = "",
    signature: str = ""
):
    """
    API này được gọi nếu dùng HTTPS deeplink thay vì custom scheme
    """
    try:
        print(f"=== Payment Callback ===")
        print(f"Order ID: {orderId}")
        print(f"Result Code: {resultCode}")
        print(f"Message: {message}")
        print(f"Trans ID: {transId}")
        
        # Verify signature nếu cần
        # ...
        
        # Redirect về app
        deeplink_url = f"pizzaapp://payment?orderId={orderId}&resultCode={resultCode}&message={message}&transId={transId}"
        
        return RedirectResponse(url=deeplink_url)
        
    except Exception as e:
        print(f"Error in payment callback: {e}")
        return RedirectResponse(url=f"pizzaapp://payment?orderId={orderId}&resultCode=99&message=error")


class DatHangRequest(BaseModel):
    ma_nguoi_dung: int
    ma_thong_tin_giao_hang: int
    phuong_thuc_thanh_toan: str  # 'tien_mat', 'chuyen_khoan', 'the_tin_dung', 'vi_dien_tu', 'momo'
    ma_giam_gia: Optional[int] = None
    ghi_chu: Optional[str] = None
    thoi_gian_giao_du_kien: Optional[str] = None

# 2. Cập nhật API đặt hàng để xử lý thanh toán MoMo
@app.post("/datHang")
def dat_hang(request: DatHangRequest):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        cursor = conn.cursor(dictionary=True)

        # === 1. Kiểm tra thông tin người dùng và giao hàng ===
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", (request.ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (request.ma_thong_tin_giao_hang, request.ma_nguoi_dung))
        thong_tin_giao_hang = cursor.fetchone()
        if not thong_tin_giao_hang:
            raise HTTPException(status_code=404, detail="Thông tin giao hàng không tồn tại")

        # === 2. Lấy giỏ hàng và mặt hàng ===
        cursor.execute("SELECT ma_gio_hang FROM GioHang WHERE ma_nguoi_dung = %s", (request.ma_nguoi_dung,))
        gio_hang = cursor.fetchone()
        if not gio_hang:
            raise HTTPException(status_code=400, detail="Giỏ hàng trống")
        ma_gio_hang = gio_hang['ma_gio_hang']

        cursor.execute("""
            SELECT mhgh.*, sp.ten_san_pham, c.ten_combo 
            FROM MatHangGioHang mhgh
            LEFT JOIN SanPham sp ON mhgh.ma_san_pham = sp.ma_san_pham
            LEFT JOIN Combo c ON mhgh.ma_combo = c.ma_combo
            WHERE mhgh.ma_gio_hang = %s
        """, (ma_gio_hang,))
        mat_hang_list = cursor.fetchall()
        if not mat_hang_list:
            raise HTTPException(status_code=400, detail="Giỏ hàng trống")

        # === 3. Tính tổng tiền ===
        tong_tien_san_pham, chi_tiet_don_hang = 0, []
        for mh in mat_hang_list:
            tong_tuy_chon = 0

            if mh['loai_mat_hang'] == 'san_pham':
                cursor.execute("""
                    SELECT gia_them FROM ChiTietTuyChonGioHang 
                    WHERE ma_mat_hang_gio_hang = %s
                """, (mh['ma_mat_hang_gio_hang'],))
                tong_tuy_chon = sum(tc['gia_them'] for tc in cursor.fetchall())

            elif mh['loai_mat_hang'] == 'combo':
                cursor.execute("""
                    SELECT SUM(tccgh.gia_them) AS tong_gia_tuy_chon
                    FROM TuyChonComboGioHang tccgh
                    JOIN ChiTietComboGioHang ctcgh ON tccgh.ma_chi_tiet_combo_gio_hang = ctcgh.ma_chi_tiet
                    WHERE ctcgh.ma_mat_hang_gio_hang = %s
                """, (mh['ma_mat_hang_gio_hang'],))
                tong_tuy_chon = cursor.fetchone()['tong_gia_tuy_chon'] or 0

            thanh_tien = (mh['gia_san_pham'] + tong_tuy_chon) * mh['so_luong']
            tong_tien_san_pham += thanh_tien
            chi_tiet_don_hang.append({'mat_hang': mh, 'tong_gia_tuy_chon': tong_tuy_chon, 'thanh_tien': thanh_tien})

        # === 4. Mã giảm giá ===
        giam_gia = 0
        if request.ma_giam_gia:
            cursor.execute("""
                SELECT * FROM MaGiamGia WHERE ma_giam_gia = %s
            """, (request.ma_giam_gia,))
            mg = cursor.fetchone()
            if not mg or not mg['hoat_dong']:
                raise HTTPException(status_code=400, detail="Mã giảm giá không hợp lệ hoặc đã hết hiệu lực")

            now = datetime.now().date()
            if now < mg['ngay_bat_dau'] or now > mg['ngay_ket_thuc']:
                raise HTTPException(status_code=400, detail="Mã giảm giá không còn hiệu lực")

            if mg['gia_tri_don_hang_toi_thieu'] and tong_tien_san_pham < mg['gia_tri_don_hang_toi_thieu']:
                raise HTTPException(status_code=400, detail="Không đủ điều kiện sử dụng mã giảm giá")

            if mg['so_lan_su_dung_toi_da'] and mg['da_su_dung'] >= mg['so_lan_su_dung_toi_da']:
                raise HTTPException(status_code=400, detail="Mã giảm giá đã hết lượt sử dụng")

            if mg['loai_giam_gia'] == 'phan_tram':
                giam_gia = tong_tien_san_pham * mg['gia_tri_giam'] / 100
            else:
                giam_gia = mg['gia_tri_giam']
            giam_gia = min(giam_gia, tong_tien_san_pham)

        # === 5. Tổng tiền cuối cùng ===
        phi_giao_hang = 0
        tong_tien_cuoi_cung = tong_tien_san_pham + phi_giao_hang - giam_gia

        # === 6. Tạo đơn hàng ===
        trang_thai_thanh_toan = 'cho_xu_ly' if request.phuong_thuc_thanh_toan == 'momo' else 'cho_xu_ly'
        
        # Đảm bảo thứ tự trùng khớp hoàn toàn với danh sách cột
        cursor.execute("""
            INSERT INTO DonHang (
                ma_thong_tin_giao_hang, ma_nguoi_dung, tong_tien_san_pham, phi_giao_hang,
                giam_gia_ma_giam_gia, giam_gia_combo, tong_tien_cuoi_cung,
                trang_thai, phuong_thuc_thanh_toan, trang_thai_thanh_toan,
                ma_giam_gia, ghi_chu, thoi_gian_giao_du_kien
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'cho_xac_nhan', %s, %s, %s, %s, %s)
        """, (
            request.ma_thong_tin_giao_hang, request.ma_nguoi_dung, tong_tien_san_pham, phi_giao_hang,
            giam_gia, 0, tong_tien_cuoi_cung,
            request.phuong_thuc_thanh_toan, trang_thai_thanh_toan,
            request.ma_giam_gia, request.ghi_chu, request.thoi_gian_giao_du_kien
        ))

        ma_don_hang = cursor.lastrowid

        # === 7. Chuyển mặt hàng từ giỏ hàng sang đơn hàng ===
        for ct in chi_tiet_don_hang:
            mh = ct['mat_hang']
            cursor.execute("""
                INSERT INTO MatHangDonHang (
                    ma_don_hang, ma_san_pham, ma_combo, loai_mat_hang,
                    so_luong, don_gia_co_ban, tong_gia_tuy_chon, thanh_tien, ghi_chu
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ma_don_hang, mh['ma_san_pham'], mh['ma_combo'], mh['loai_mat_hang'],
                mh['so_luong'], mh['gia_san_pham'], ct['tong_gia_tuy_chon'], ct['thanh_tien'], mh['ghi_chu']
            ))
            ma_mh_dh = cursor.lastrowid

            # Xử lý tùy chọn sản phẩm
            if mh['loai_mat_hang'] == 'san_pham':
                cursor.execute("""
                    SELECT cttcgh.*, gtc.ten_gia_tri, ltc.ten_loai
                    FROM ChiTietTuyChonGioHang cttcgh
                    JOIN GiaTriTuyChon gtc ON cttcgh.ma_gia_tri = gtc.ma_gia_tri
                    JOIN LoaiTuyChon ltc ON gtc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
                    WHERE cttcgh.ma_mat_hang_gio_hang = %s
                """, (mh['ma_mat_hang_gio_hang'],))
                for row in cursor.fetchall():
                    cursor.execute("""
                        INSERT INTO ChiTietTuyChonDonHang (
                            ma_mat_hang_don_hang, ma_gia_tri, ten_loai_tuy_chon, ten_gia_tri, gia_them
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (ma_mh_dh, row['ma_gia_tri'], row['ten_loai'], row['ten_gia_tri'], row['gia_them']))

            # Xử lý tùy chọn combo
            elif mh['loai_mat_hang'] == 'combo':
                cursor.execute("""
                    SELECT ctcgh.*, ctc.ten_san_pham, ctc.ma_san_pham, ctc.gia_san_pham
                    FROM ChiTietComboGioHang ctcgh
                    JOIN ChiTietCombo ctc ON ctcgh.ma_chi_tiet_combo = ctc.ma_chi_tiet_combo
                    WHERE ctcgh.ma_mat_hang_gio_hang = %s
                """, (mh['ma_mat_hang_gio_hang'],))
                for ctc in cursor.fetchall():
                    cursor.execute("""
                        INSERT INTO ChiTietComboDonHang (
                            ma_mat_hang_don_hang, ma_san_pham, ten_san_pham, so_luong, don_gia
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (ma_mh_dh, ctc['ma_san_pham'], ctc['ten_san_pham'], ctc['so_luong'], ctc['gia_san_pham']))
                    ma_ctc_dh = cursor.lastrowid

                    # Tùy chọn cho combo
                    cursor.execute("""
                        SELECT tccgh.*, gtc.ten_gia_tri, ltc.ten_loai
                        FROM TuyChonComboGioHang tccgh
                        JOIN GiaTriTuyChon gtc ON tccgh.ma_gia_tri = gtc.ma_gia_tri
                        JOIN LoaiTuyChon ltc ON gtc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
                        WHERE tccgh.ma_chi_tiet_combo_gio_hang = %s
                    """, (ctc['ma_chi_tiet'],))
                    for tcc in cursor.fetchall():
                        cursor.execute("""
                            INSERT INTO TuyChonComboDonHang (
                                ma_chi_tiet_combo_don_hang, ma_gia_tri, ten_loai_tuy_chon, ten_gia_tri, gia_them
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (ma_ctc_dh, tcc['ma_gia_tri'], tcc['ten_loai'], tcc['ten_gia_tri'], tcc['gia_them']))

        # === 8. Cập nhật mã giảm giá ===
        if request.ma_giam_gia:
            cursor.execute("UPDATE MaGiamGia SET da_su_dung = da_su_dung + 1 WHERE ma_giam_gia = %s", (request.ma_giam_gia,))
        
        # === 9. XÓA GIỎ HÀNG NGAY SAU KHI TẠO ĐỢN HÀNG THÀNH CÔNG ===
        cursor.execute("DELETE FROM MatHangGioHang WHERE ma_gio_hang = %s", (ma_gio_hang,))
        
        # === 10. Tạo giao dịch ===
        cursor.execute("""
            INSERT INTO GiaoDich (ma_nguoi_dung, loai_giao_dich, so_tien, trang_thai, phuong_thuc_thanh_toan)
            VALUES (%s, 'thanh_toan_don_hang', %s, %s, %s)
        """, (
            request.ma_nguoi_dung, 
            tong_tien_cuoi_cung, 
            'cho_xu_ly' if request.phuong_thuc_thanh_toan == 'momo' else 'cho_xu_ly',
            request.phuong_thuc_thanh_toan
        ))

        # === 11. Xử lý thanh toán MoMo ===
        if request.phuong_thuc_thanh_toan == 'momo':
            try:
                # Tạo URL thanh toán MoMo
                payment_data = PaymentRequest(
                    so_tien=int(tong_tien_cuoi_cung),
                    phuong_thuc="momo",
                    ma_don_hang=ma_don_hang
                )
                
                # Gọi hàm tạo URL thanh toán
                payment_result = tao_url_thanh_toan(payment_data)
                
                if payment_result.get("resultCode") == 0:
                    # Commit transaction - giỏ hàng đã được xóa
                    conn.commit()
                    
                    return {
                        "message": "Đặt hàng thành công",
                        "ma_don_hang": ma_don_hang,
                        "tong_tien_cuoi_cung": tong_tien_cuoi_cung,
                        "phuong_thuc_thanh_toan": "momo",
                        "payment_url": payment_result.get("payUrl"),
                        "qr_code_url": payment_result.get("qrCodeUrl"),
                        "deep_link": payment_result.get("deeplink"),
                        "thong_tin_giao_hang": {
                            "ten_nguoi_nhan": thong_tin_giao_hang['ten_nguoi_nhan'],
                            "so_dien_thoai": thong_tin_giao_hang['so_dien_thoai_nguoi_nhan'],
                            "dia_chi": f"{thong_tin_giao_hang['so_duong']}, {thong_tin_giao_hang['phuong_xa']}, {thong_tin_giao_hang['quan_huyen']}, {thong_tin_giao_hang['tinh_thanh_pho']}"
                        }
                    }
                else:
                    # Nếu tạo URL thanh toán thất bại, rollback tất cả
                    conn.rollback()
                    raise HTTPException(status_code=500, detail="Không thể tạo URL thanh toán MoMo")
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Lỗi tạo thanh toán MoMo: {str(e)}")
        
        # === 12. Commit transaction cho các phương thức thanh toán khác ===
        conn.commit()
        
        # Trả về kết quả cho các phương thức thanh toán khác
        return {
            "message": "Đặt hàng thành công",
            "ma_don_hang": ma_don_hang,
            "tong_tien_san_pham": tong_tien_san_pham,
            "phi_giao_hang": phi_giao_hang,
            "giam_gia_ma_giam_gia": giam_gia,
            "tong_tien_cuoi_cung": tong_tien_cuoi_cung,
            "thong_tin_giao_hang": {
                "ten_nguoi_nhan": thong_tin_giao_hang['ten_nguoi_nhan'],
                "so_dien_thoai": thong_tin_giao_hang['so_dien_thoai_nguoi_nhan'],
                "dia_chi": f"{thong_tin_giao_hang['so_duong']}, {thong_tin_giao_hang['phuong_xa']}, {thong_tin_giao_hang['quan_huyen']}, {thong_tin_giao_hang['tinh_thanh_pho']}"
            }
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    finally:
        if conn:
            conn.close()

# Cách 2: Sử dụng model riêng cho MoMo callback
@app.post("/momo-ipn")
async def momo_ipn(request: Request):
    try:
        # Lấy raw body
        body = await request.body()
        print(f"=== MoMo IPN Raw Body ===")
        print(f"Body: {body}")
        
        # Lấy headers để debug
        print(f"=== Headers ===")
        for name, value in request.headers.items():
            print(f"{name}: {value}")
        
        # Parse JSON
        try:
            data = json.loads(body)
            print(f"=== MoMo IPN Parsed Data ===")
            print(f"Data: {data}")
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            # Thử parse form data
            try:
                form_data = await request.form()
                data = dict(form_data)
                print(f"=== Form Data ===")
                print(f"Data: {data}")
            except Exception as form_error:
                print(f"Form parse error: {form_error}")
                return {"message": "Invalid data format"}
        
        # Lấy thông tin từ data (an toàn) - đổi tên biến theo database
        ma_don_hang = data.get('orderId', '')
        ma_ket_qua = str(data.get('resultCode', ''))
        so_tien = data.get('amount', 0)
        thong_bao = data.get('message', '')
        chu_ky_nhan = data.get('signature', '')
        ma_yeu_cau = data.get('requestId', '')
        ma_doi_tac = data.get('partnerCode', '')
        ma_giao_dich_momo = data.get('transId', '')
        
        # Convert amount to int if it's string
        try:
            so_tien = int(so_tien)
        except (ValueError, TypeError):
            so_tien = 0
        
        # Log thông tin chính
        print(f"=== MoMo IPN Processing ===")
        print(f"Mã đơn hàng: {ma_don_hang}")
        print(f"Mã kết quả: {ma_ket_qua}")
        print(f"Số tiền: {so_tien}")
        print(f"Thông báo: {thong_bao}")
        print(f"Mã đối tác: {ma_doi_tac}")
        print(f"Mã giao dịch MoMo: {ma_giao_dich_momo}")
        print(f"Chữ ký: {chu_ky_nhan}")
        
        # Validate required fields
        if not ma_don_hang:
            print("Thiếu mã đơn hàng")
            return {"message": "Missing orderId"}
        
        if not ma_ket_qua:
            print("Thiếu mã kết quả")
            return {"message": "Missing resultCode"}
        
        # Kết nối database với retry logic
        conn = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = db.connect_to_database()
                if isinstance(conn, Error):
                    if attempt == max_retries - 1:
                        print(f"Database connection failed after {max_retries} attempts")
                        return {"message": "Database connection error"}
                    continue
                break
            except Exception as e:
                print(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"message": "Database connection error"}
                continue
        
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra đơn hàng có tồn tại không
        cursor.execute("SELECT * FROM DonHang WHERE ma_don_hang = %s", (ma_don_hang,))
        don_hang = cursor.fetchone()
        
        if not don_hang:
            print(f"Không tìm thấy đơn hàng: {ma_don_hang}")
            return {"message": "Order not found"}
        
        print(f"Tìm thấy đơn hàng: {don_hang}")
        
        # Kiểm tra xem đơn hàng đã được xử lý chưa
        if don_hang.get('trang_thai_thanh_toan') == 'hoan_thanh':
            print(f"Đơn hàng {ma_don_hang} đã được xử lý")
            return {"message": "Order already processed"}
        
        # Xử lý theo kết quả thanh toán
        if ma_ket_qua == "0":  # Thanh toán thành công
            print(f"Xử lý thanh toán thành công cho đơn hàng {ma_don_hang}")
            
            # Cập nhật đơn hàng
            cursor.execute("""
                UPDATE DonHang 
                SET trang_thai_thanh_toan = 'hoan_thanh',
                    trang_thai = 'cho_xac_nhan',
                    ngay_cap_nhat = NOW()
                WHERE ma_don_hang = %s
            """, (ma_don_hang,))
            
            so_dong_cap_nhat_don_hang = cursor.rowcount
            print(f"Đã cập nhật {so_dong_cap_nhat_don_hang} bản ghi đơn hàng")
            
            # Cập nhật giao dịch
            print(f"Cập nhật giao dịch cho người dùng: {don_hang['ma_nguoi_dung']}")
            
            # Tìm giao dịch phù hợp
            cursor.execute("""
                SELECT * FROM GiaoDich 
                WHERE ma_nguoi_dung = %s
                AND phuong_thuc_thanh_toan = 'momo' 
                AND trang_thai = 'cho_xu_ly'
                AND (ABS(so_tien - %s) < 100 OR so_tien = %s)
                ORDER BY ngay_tao DESC 
                LIMIT 1
            """, (don_hang['ma_nguoi_dung'], so_tien, don_hang.get('tong_tien_cuoi_cung', so_tien)))
            
            giao_dich_phu_hop = cursor.fetchone()
            
            if giao_dich_phu_hop:
                cursor.execute("""
                    UPDATE GiaoDich 
                    SET trang_thai = 'hoan_thanh'
                    WHERE ma_giao_dich = %s
                """, (giao_dich_phu_hop['ma_giao_dich'],))
                
                so_dong_cap_nhat_giao_dich = cursor.rowcount
                print(f"Đã cập nhật {so_dong_cap_nhat_giao_dich} bản ghi giao dịch")
            else:
                print("Không tìm thấy giao dịch phù hợp")
                # Tạo giao dịch mới nếu không tìm thấy
                cursor.execute("""
                    INSERT INTO GiaoDich (
                        ma_nguoi_dung, so_tien, phuong_thuc_thanh_toan, 
                        trang_thai, loai_giao_dich, ngay_tao
                    ) VALUES (%s, %s, 'momo', 'hoan_thanh', 'thanh_toan_don_hang', NOW())
                """, (don_hang['ma_nguoi_dung'], so_tien))
                
                print("Đã tạo bản ghi giao dịch mới")
                
        else:  # Thanh toán thất bại
            print(f"Xử lý thanh toán thất bại cho đơn hàng {ma_don_hang}")
            
            cursor.execute("""
                UPDATE DonHang 
                SET trang_thai_thanh_toan = 'that_bai',
                    trang_thai = 'da_huy',
                    ngay_cap_nhat = NOW()
                WHERE ma_don_hang = %s
            """, (ma_don_hang,))
            
            cursor.execute("""
                UPDATE GiaoDich 
                SET trang_thai = 'that_bai'
                WHERE ma_nguoi_dung = %s
                AND phuong_thuc_thanh_toan = 'momo' 
                AND trang_thai = 'cho_xu_ly'
                ORDER BY ngay_tao DESC 
                LIMIT 1
            """, (don_hang['ma_nguoi_dung'],))
            
            # Hoàn lại mã giảm giá
            if don_hang.get('ma_giam_gia'):
                cursor.execute("""
                    UPDATE MaGiamGia 
                    SET da_su_dung = GREATEST(da_su_dung - 1, 0)
                    WHERE ma_giam_gia = %s
                """, (don_hang['ma_giam_gia'],))
                print(f"Đã hoàn lại mã giảm giá: {don_hang['ma_giam_gia']}")
        
        # Commit changes
        conn.commit()
        print(f"Đã commit database thành công cho đơn hàng {ma_don_hang}")
        
        # Kiểm tra kết quả sau khi update
        cursor.execute("SELECT trang_thai, trang_thai_thanh_toan FROM DonHang WHERE ma_don_hang = %s", (ma_don_hang,))
        ket_qua_don_hang = cursor.fetchone()
        print(f"Trạng thái đơn hàng sau khi cập nhật: {ket_qua_don_hang}")
        
        cursor.execute("""
            SELECT trang_thai FROM GiaoDich 
            WHERE ma_nguoi_dung = %s AND phuong_thuc_thanh_toan = 'momo'
            ORDER BY ngay_tao DESC LIMIT 1
        """, (don_hang['ma_nguoi_dung'],))
        ket_qua_giao_dich = cursor.fetchone()
        print(f"Trạng thái giao dịch sau khi cập nhật: {ket_qua_giao_dich}")
        
        # Trả về response cho MoMo
        return {
            "message": "OK", 
            "status": "success", 
            "orderId": ma_don_hang,
            "resultCode": ma_ket_qua
        }
        
    except Exception as e:
        print(f"Lỗi trong MoMo IPN: {str(e)}")
        traceback.print_exc()
        
        # Rollback nếu có lỗi
        if 'conn' in locals() and conn:
            try:
                conn.rollback()
                print("Đã rollback database")
            except:
                pass
        
        return {"message": f"Error: {str(e)}", "status": "error"}
    
    finally:
        # Đóng connection
        if 'conn' in locals() and conn:
            try:
                conn.close()
                print("Đã đóng kết nối database")
            except:
                pass
# API để test callback thủ công
@app.post("/test-momo-payment/{order_id}")
async def test_momo_payment(order_id: str):
    """Test API để simulate MoMo callback"""
    try:
        # Tạo fake MoMo request
        fake_request = MoMoIPNRequest(
            partnerCode="MOMO",
            orderId=order_id,
            requestId="test-request-id",
            amount=100000,
            orderInfo=f"Test payment for order {order_id}",
            orderType="momo_wallet",
            transId="test-trans-id",
            resultCode="0",  # Thành công
            message="Successful.",
            payType="qr",
            responseTime="1234567890",
            extraData="",
            signature="test-signature"
        )
        
        # Gọi hàm IPN
        result = await momo_ipn(fake_request)
        return result
        
    except Exception as e:
        return {"message": f"Test error: {str(e)}"}

# API để kiểm tra trạng thái chi tiết
@app.get("/debug-order/{order_id}")
async def debug_order(order_id: str):
    """Debug API để kiểm tra trạng thái đơn hàng và giao dịch"""
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Lấy thông tin đơn hàng
        cursor.execute("SELECT * FROM DonHang WHERE ma_don_hang = %s", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return {"message": "Order not found"}
        
        # Lấy thông tin giao dịch
        cursor.execute("""
            SELECT * FROM GiaoDich 
            WHERE ma_nguoi_dung = %s 
            ORDER BY thoi_gian_tao DESC
        """, (order['ma_nguoi_dung'],))
        transactions = cursor.fetchall()
        
        return {
            "order": order,
            "transactions": transactions,
            "momo_transactions": [t for t in transactions if t['phuong_thuc_thanh_toan'] == 'momo']
        }
        
    except Exception as e:
        return {"message": f"Debug error: {str(e)}"}
    finally:
        if 'conn' in locals():
            conn.close()

# 4. API kiểm tra trạng thái thanh toán
@app.get("/kiem-tra-thanh-toan/{ma_don_hang}")
def kiem_tra_thanh_toan(ma_don_hang: int):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT dh.trang_thai_thanh_toan, dh.trang_thai, dh.phuong_thuc_thanh_toan, dh.ma_nguoi_dung,
                   gd.trang_thai as trang_thai_giao_dich
            FROM DonHang dh
            LEFT JOIN GiaoDich gd ON dh.ma_nguoi_dung = gd.ma_nguoi_dung 
                AND gd.phuong_thuc_thanh_toan = dh.phuong_thuc_thanh_toan
                AND gd.so_tien = dh.tong_tien_cuoi_cung
            WHERE dh.ma_don_hang = %s
            ORDER BY gd.ngay_tao DESC
            LIMIT 1
        """, (ma_don_hang,))
        
        don_hang = cursor.fetchone()
        if not don_hang:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")
        
        return {
            "ma_don_hang": ma_don_hang,
            "trang_thai_thanh_toan": don_hang['trang_thai_thanh_toan'],
            "trang_thai_don_hang": don_hang['trang_thai'],
            "phuong_thuc_thanh_toan": don_hang['phuong_thuc_thanh_toan'],
            "trang_thai_giao_dich": don_hang['trang_thai_giao_dich']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

# Response Models (vẫn giữ nguyên)

class MaGiamGiaResponse(BaseModel):
    ma_giam_gia: int
    ma_code: str
    loai_giam_gia: str
    gia_tri_giam: Decimal
    ngay_bat_dau: date
    ngay_ket_thuc: date
    gia_tri_don_hang_toi_thieu: Optional[Decimal]
    so_lan_su_dung_toi_da: Optional[int]
    da_su_dung: int
    hoat_dong: bool
    ngay_tao: datetime

class KiemTraMaGiamGiaResponse(BaseModel):
    hop_le: bool
    thong_bao: str
    gia_tri_giam: Optional[Decimal] = None
    loai_giam_gia: Optional[str] = None
    gia_tri_don_hang_toi_thieu: Optional[Decimal] = None

class ListMaGiamGiaResponse(BaseModel):
    danh_sach_ma_giam_gia: List[MaGiamGiaResponse]
    tong_so_ma: int
    trang_hien_tai: int
    tong_so_trang: int

# API tạo mã giảm giá - Form Data
@app.post("/maGiamGia/tao")
def tao_ma_giam_gia(
    ma_code: str = Form(..., description="Mã giảm giá"),
    loai_giam_gia: str = Form(..., description="Loại giảm giá: 'phan_tram' hoặc 'co_dinh'"),
    gia_tri_giam: Decimal = Form(..., description="Giá trị giảm"),
    ngay_bat_dau: date = Form(..., description="Ngày bắt đầu"),
    ngay_ket_thuc: date = Form(..., description="Ngày kết thúc"),
    gia_tri_don_hang_toi_thieu: Optional[Decimal] = Form(None, description="Giá trị đơn hàng tối thiểu"),
    so_lan_su_dung_toi_da: Optional[int] = Form(None, description="Số lần sử dụng tối đa")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Kiểm tra độ dài mã code
        if len(ma_code) < 1 or len(ma_code) > 50:
            raise HTTPException(status_code=400, detail="Mã giảm giá phải có độ dài từ 1-50 ký tự")

        # Kiểm tra giá trị giảm
        if gia_tri_giam <= 0:
            raise HTTPException(status_code=400, detail="Giá trị giảm phải lớn hơn 0")

        # Kiểm tra loại giảm giá hợp lệ
        if loai_giam_gia not in ['phan_tram', 'co_dinh']:
            raise HTTPException(status_code=400, detail="Loại giảm giá không hợp lệ")

        # Kiểm tra ngày hợp lệ
        if ngay_bat_dau >= ngay_ket_thuc:
            raise HTTPException(status_code=400, detail="Ngày bắt đầu phải trước ngày kết thúc")

        # Kiểm tra mã code đã tồn tại
        cursor.execute("SELECT ma_giam_gia FROM MaGiamGia WHERE ma_code = %s", (ma_code,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Mã giảm giá đã tồn tại")

        # Thêm mã giảm giá mới
        insert_query = """
            INSERT INTO MaGiamGia (ma_code, loai_giam_gia, gia_tri_giam, ngay_bat_dau, 
                                   ngay_ket_thuc, gia_tri_don_hang_toi_thieu, so_lan_su_dung_toi_da)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            ma_code,
            loai_giam_gia,
            gia_tri_giam,
            ngay_bat_dau,
            ngay_ket_thuc,
            gia_tri_don_hang_toi_thieu,
            so_lan_su_dung_toi_da
        ))

        conn.commit()
        ma_giam_gia_id = cursor.lastrowid

        return {
            "message": "Tạo mã giảm giá thành công",
            "ma_giam_gia": ma_giam_gia_id,
            "ma_code": ma_code
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API lấy toàn bộ danh sách mã giảm giá (không phân trang) - Query params
@app.get("/maGiamGia/danhSach")
def lay_toan_bo_danh_sach_ma_giam_gia(
    hoat_dong: Optional[bool] = Query(None, description="Lọc theo trạng thái hoạt động"),
    loai_giam_gia: Optional[str] = Query(None, description="Lọc theo loại giảm giá")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Xây dựng điều kiện lọc
        where_conditions = []
        params = []

        if hoat_dong is not None:
            where_conditions.append("hoat_dong = %s")
            params.append(hoat_dong)

        if loai_giam_gia:
            where_conditions.append("loai_giam_gia = %s")
            params.append(loai_giam_gia)

        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # Lấy toàn bộ danh sách không phân trang
        query = f"""
            SELECT ma_giam_gia, ma_code, loai_giam_gia, gia_tri_giam, ngay_bat_dau,
                   ngay_ket_thuc, gia_tri_don_hang_toi_thieu, so_lan_su_dung_toi_da,
                   da_su_dung, hoat_dong, ngay_tao
            FROM MaGiamGia
            {where_clause}
            ORDER BY ngay_tao DESC
        """
        cursor.execute(query, params)

        danh_sach_ma_giam_gia = []
        for row in cursor.fetchall():
            ma_giam_gia = MaGiamGiaResponse(
                ma_giam_gia=row[0],
                ma_code=row[1],
                loai_giam_gia=row[2],
                gia_tri_giam=row[3],
                ngay_bat_dau=row[4],
                ngay_ket_thuc=row[5],
                gia_tri_don_hang_toi_thieu=row[6],
                so_lan_su_dung_toi_da=row[7],
                da_su_dung=row[8],
                hoat_dong=row[9],
                ngay_tao=row[10]
            )
            danh_sach_ma_giam_gia.append(ma_giam_gia)

        return {
            "danh_sach_ma_giam_gia": danh_sach_ma_giam_gia,
            "tong_so_ma": len(danh_sach_ma_giam_gia)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API kiểm tra mã giảm giá - Form Data
@app.post("/maGiamGia/kiemTra")
def kiem_tra_ma_giam_gia(
    ma_code: str = Form(..., description="Mã giảm giá"),
    ma_nguoi_dung: int = Form(..., description="Mã người dùng"),
    tong_gia_tri_don_hang: Decimal = Form(..., description="Tổng giá trị đơn hàng")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Lấy thông tin mã giảm giá
        cursor.execute("""
            SELECT ma_giam_gia, loai_giam_gia, gia_tri_giam, ngay_bat_dau, ngay_ket_thuc,
                   gia_tri_don_hang_toi_thieu, so_lan_su_dung_toi_da, da_su_dung, hoat_dong
            FROM MaGiamGia 
            WHERE ma_code = %s
        """, (ma_code,))

        ma_giam_gia_data = cursor.fetchone()
        if not ma_giam_gia_data:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Mã giảm giá không tồn tại"
            )

        ma_giam_gia_id, loai_giam_gia, gia_tri_giam, ngay_bat_dau, ngay_ket_thuc, \
        gia_tri_don_hang_toi_thieu, so_lan_su_dung_toi_da, da_su_dung, hoat_dong = ma_giam_gia_data

        # Kiểm tra các điều kiện
        ngay_hien_tai = date.today()

        # Kiểm tra mã có hoạt động không
        if not hoat_dong:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Mã giảm giá đã bị vô hiệu hóa"
            )

        # Kiểm tra thời gian hiệu lực
        if ngay_hien_tai < ngay_bat_dau:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Mã giảm giá chưa có hiệu lực"
            )

        if ngay_hien_tai > ngay_ket_thuc:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Mã giảm giá đã hết hạn"
            )

        # Kiểm tra số lần sử dụng
        if so_lan_su_dung_toi_da and da_su_dung >= so_lan_su_dung_toi_da:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Mã giảm giá đã hết lượt sử dụng"
            )

        # Kiểm tra giá trị đơn hàng tối thiểu
        if gia_tri_don_hang_toi_thieu and tong_gia_tri_don_hang < gia_tri_don_hang_toi_thieu:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao=f"Đơn hàng phải có giá trị tối thiểu {gia_tri_don_hang_toi_thieu:,}đ"
            )

        # Kiểm tra người dùng đã sử dụng mã này chưa (nếu có giới hạn)
        cursor.execute("""
            SELECT so_lan_su_dung 
            FROM MaGiamGiaNguoiDung 
            WHERE ma_nguoi_dung = %s AND ma_giam_gia = %s
        """, (ma_nguoi_dung, ma_giam_gia_id))

        nguoi_dung_su_dung = cursor.fetchone()
        if nguoi_dung_su_dung and nguoi_dung_su_dung[0] > 0:
            return KiemTraMaGiamGiaResponse(
                hop_le=False,
                thong_bao="Bạn đã sử dụng mã giảm giá này rồi"
            )

        # Tính giá trị giảm
        gia_tri_giam_tinh = gia_tri_giam
        if loai_giam_gia == 'phan_tram':
            gia_tri_giam_tinh = tong_gia_tri_don_hang * gia_tri_giam / 100

        return KiemTraMaGiamGiaResponse(
            hop_le=True,
            thong_bao="Mã giảm giá hợp lệ",
            gia_tri_giam=gia_tri_giam_tinh,
            loai_giam_gia=loai_giam_gia,
            gia_tri_don_hang_toi_thieu=gia_tri_don_hang_toi_thieu
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API áp dụng mã giảm giá - Form Data
@app.post("/maGiamGia/apDung")
def ap_dung_ma_giam_gia(
    ma_code: str = Form(..., description="Mã giảm giá"),
    ma_nguoi_dung: int = Form(..., description="Mã người dùng"),
    tong_gia_tri_don_hang: Decimal = Form(..., description="Tổng giá trị đơn hàng")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Kiểm tra mã giảm giá trước
        kiem_tra_result = kiem_tra_ma_giam_gia(ma_code, ma_nguoi_dung, tong_gia_tri_don_hang)
        if not kiem_tra_result.hop_le:
            return kiem_tra_result

        # Lấy ID mã giảm giá
        cursor.execute("SELECT ma_giam_gia FROM MaGiamGia WHERE ma_code = %s", (ma_code,))
        ma_giam_gia_id = cursor.fetchone()[0]

        # Cập nhật số lần sử dụng của mã giảm giá
        cursor.execute("""
            UPDATE MaGiamGia 
            SET da_su_dung = da_su_dung + 1 
            WHERE ma_giam_gia = %s
        """, (ma_giam_gia_id,))

        # Thêm/cập nhật lịch sử sử dụng của người dùng
        cursor.execute("""
            INSERT INTO MaGiamGiaNguoiDung (ma_nguoi_dung, ma_giam_gia, so_lan_su_dung)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE so_lan_su_dung = so_lan_su_dung + 1
        """, (ma_nguoi_dung, ma_giam_gia_id))

        conn.commit()

        return {
            "message": "Áp dụng mã giảm giá thành công",
            "gia_tri_giam": kiem_tra_result.gia_tri_giam,
            "loai_giam_gia": kiem_tra_result.loai_giam_gia
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API cập nhật mã giảm giá - Form Data
@app.put("/maGiamGia/{ma_giam_gia_id}")
def cap_nhat_ma_giam_gia(
    ma_giam_gia_id: int,
    ma_code: Optional[str] = Form(None, description="Mã giảm giá"),
    loai_giam_gia: Optional[str] = Form(None, description="Loại giảm giá"),
    gia_tri_giam: Optional[Decimal] = Form(None, description="Giá trị giảm"),
    ngay_bat_dau: Optional[date] = Form(None, description="Ngày bắt đầu"),
    ngay_ket_thuc: Optional[date] = Form(None, description="Ngày kết thúc"),
    gia_tri_don_hang_toi_thieu: Optional[Decimal] = Form(None, description="Giá trị đơn hàng tối thiểu"),
    so_lan_su_dung_toi_da: Optional[int] = Form(None, description="Số lần sử dụng tối đa"),
    hoat_dong: Optional[bool] = Form(None, description="Trạng thái hoạt động")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Kiểm tra mã giảm giá tồn tại
        cursor.execute("SELECT ma_giam_gia FROM MaGiamGia WHERE ma_giam_gia = %s", (ma_giam_gia_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Mã giảm giá không tồn tại")

        # Xây dựng câu update
        update_fields = []
        params = []

        if ma_code is not None:
            if len(ma_code) < 1 or len(ma_code) > 50:
                raise HTTPException(status_code=400, detail="Mã giảm giá phải có độ dài từ 1-50 ký tự")
            update_fields.append("ma_code = %s")
            params.append(ma_code)

        if loai_giam_gia is not None:
            if loai_giam_gia not in ['phan_tram', 'co_dinh']:
                raise HTTPException(status_code=400, detail="Loại giảm giá không hợp lệ")
            update_fields.append("loai_giam_gia = %s")
            params.append(loai_giam_gia)

        if gia_tri_giam is not None:
            if gia_tri_giam <= 0:
                raise HTTPException(status_code=400, detail="Giá trị giảm phải lớn hơn 0")
            update_fields.append("gia_tri_giam = %s")
            params.append(gia_tri_giam)

        if ngay_bat_dau is not None:
            update_fields.append("ngay_bat_dau = %s")
            params.append(ngay_bat_dau)

        if ngay_ket_thuc is not None:
            update_fields.append("ngay_ket_thuc = %s")
            params.append(ngay_ket_thuc)

        if gia_tri_don_hang_toi_thieu is not None:
            update_fields.append("gia_tri_don_hang_toi_thieu = %s")
            params.append(gia_tri_don_hang_toi_thieu)

        if so_lan_su_dung_toi_da is not None:
            update_fields.append("so_lan_su_dung_toi_da = %s")
            params.append(so_lan_su_dung_toi_da)

        if hoat_dong is not None:
            update_fields.append("hoat_dong = %s")
            params.append(hoat_dong)

        if not update_fields:
            raise HTTPException(status_code=400, detail="Không có trường nào để cập nhật")

        # Kiểm tra ngày hợp lệ nếu cả hai ngày đều được cung cấp
        if ngay_bat_dau is not None and ngay_ket_thuc is not None:
            if ngay_bat_dau >= ngay_ket_thuc:
                raise HTTPException(status_code=400, detail="Ngày bắt đầu phải trước ngày kết thúc")

        params.append(ma_giam_gia_id)
        update_query = f"UPDATE MaGiamGia SET {', '.join(update_fields)} WHERE ma_giam_gia = %s"
        cursor.execute(update_query, params)

        conn.commit()

        return {"message": "Cập nhật mã giảm giá thành công"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API xóa mã giảm giá - Path parameter
@app.delete("/maGiamGia/{ma_giam_gia_id}")
def xoa_ma_giam_gia(ma_giam_gia_id: int):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Kiểm tra mã giảm giá tồn tại
        cursor.execute("SELECT ma_giam_gia FROM MaGiamGia WHERE ma_giam_gia = %s", (ma_giam_gia_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Mã giảm giá không tồn tại")

        # Xóa mã giảm giá
        cursor.execute("DELETE FROM MaGiamGia WHERE ma_giam_gia = %s", (ma_giam_gia_id,))
        conn.commit()

        return {"message": "Xóa mã giảm giá thành công"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API lấy thông tin chi tiết mã giảm giá - Path parameter
@app.get("/maGiamGia/{ma_giam_gia_id}")
def lay_thong_tin_ma_giam_gia(ma_giam_gia_id: int):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ma_giam_gia, ma_code, loai_giam_gia, gia_tri_giam, ngay_bat_dau,
                   ngay_ket_thuc, gia_tri_don_hang_toi_thieu, so_lan_su_dung_toi_da,
                   da_su_dung, hoat_dong, ngay_tao
            FROM MaGiamGia 
            WHERE ma_giam_gia = %s
        """, (ma_giam_gia_id,))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Mã giảm giá không tồn tại")

        ma_giam_gia = MaGiamGiaResponse(
            ma_giam_gia=row[0],
            ma_code=row[1],
            loai_giam_gia=row[2],
            gia_tri_giam=row[3],
            ngay_bat_dau=row[4],
            ngay_ket_thuc=row[5],
            gia_tri_don_hang_toi_thieu=row[6],
            so_lan_su_dung_toi_da=row[7],
            da_su_dung=row[8],
            hoat_dong=row[9],
            ngay_tao=row[10]
        )

        return ma_giam_gia

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API lấy danh sách mã giảm giá của người dùng - Path parameter
@app.get("/maGiamGia/nguoiDung/{ma_nguoi_dung}")
def lay_ma_giam_gia_nguoi_dung(ma_nguoi_dung: int):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT mg.ma_giam_gia, mg.ma_code, mg.loai_giam_gia, mg.gia_tri_giam, 
                   mg.ngay_bat_dau, mg.ngay_ket_thuc, mg.gia_tri_don_hang_toi_thieu,
                   mg.so_lan_su_dung_toi_da, mg.da_su_dung, mg.hoat_dong, mg.ngay_tao,
                   mgnd.so_lan_su_dung as nguoi_dung_da_su_dung
            FROM MaGiamGia mg
            LEFT JOIN MaGiamGiaNguoiDung mgnd ON mg.ma_giam_gia = mgnd.ma_giam_gia 
                                                AND mgnd.ma_nguoi_dung = %s
            WHERE mg.hoat_dong = 1 
              AND mg.ngay_bat_dau <= CURDATE() 
              AND mg.ngay_ket_thuc >= CURDATE()
              AND (mg.so_lan_su_dung_toi_da IS NULL OR mg.da_su_dung < mg.so_lan_su_dung_toi_da)
              AND (mgnd.so_lan_su_dung IS NULL OR mgnd.so_lan_su_dung = 0)
            ORDER BY mg.ngay_tao DESC
        """, (ma_nguoi_dung,))

        danh_sach_ma_giam_gia = []
        for row in cursor.fetchall():
            ma_giam_gia = MaGiamGiaResponse(
                ma_giam_gia=row[0],
                ma_code=row[1],
                loai_giam_gia=row[2],
                gia_tri_giam=row[3],
                ngay_bat_dau=row[4],
                ngay_ket_thuc=row[5],
                gia_tri_don_hang_toi_thieu=row[6],
                so_lan_su_dung_toi_da=row[7],
                da_su_dung=row[8],
                hoat_dong=row[9],
                ngay_tao=row[10]
            )
            danh_sach_ma_giam_gia.append(ma_giam_gia)

        return {
            "message": "Lấy danh sách mã giảm giá thành công",
            "danh_sach_ma_giam_gia": danh_sach_ma_giam_gia,
            "so_luong": len(danh_sach_ma_giam_gia)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()
        
# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.put("/capNhatTrangThaiDonHang/{ma_don_hang}")
def cap_nhat_trang_thai_don_hang(
    ma_don_hang: int,
    trang_thai: Optional[str] = Form(None),
    trang_thai_thanh_toan: Optional[str] = Form(None)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        cursor = conn.cursor()

        # Kiểm tra đơn hàng tồn tại
        cursor.execute("SELECT * FROM DonHang WHERE ma_don_hang = %s", (ma_don_hang,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")

        # Xây dựng câu truy vấn động
        updates = []
        params = []

        if trang_thai:
            updates.append("trang_thai = %s")
            params.append(trang_thai)

        if trang_thai_thanh_toan:
            updates.append("trang_thai_thanh_toan = %s")
            params.append(trang_thai_thanh_toan)

        if not updates:
            return {"message": "Không có thông tin nào được cập nhật"}

        update_query = f"""
            UPDATE DonHang
            SET {", ".join(updates)}
            WHERE ma_don_hang = %s
        """
        params.append(ma_don_hang)

        cursor.execute(update_query, tuple(params))
        conn.commit()

        return {"message": "Cập nhật trạng thái đơn hàng thành công"}

    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

class HuyDonHangRequest(BaseModel):
    ly_do: str | None = None

@app.put("/huyDonHang/{ma_don_hang}")
def huy_don_hang(ma_don_hang: int, request: HuyDonHangRequest):
    print(">>> Hủy đơn hàng:", ma_don_hang)
    print(">>> Lý do hủy:", request.ly_do)
    
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    
    try:
        with conn.cursor() as cursor:
            # Lấy trạng thái đơn hàng
            cursor.execute("SELECT trang_thai FROM DonHang WHERE ma_don_hang = %s", (ma_don_hang,))
            result = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng")

            trang_thai = result[0]
            if trang_thai != "cho_xac_nhan":
                raise HTTPException(status_code=400, detail="Chỉ được hủy đơn hàng khi ở trạng thái 'chờ xác nhận'")

            # Hủy đơn hàng và cập nhật lý do hủy
            cursor.execute("""
                UPDATE DonHang
                SET trang_thai = 'da_huy', 
                    trang_thai_thanh_toan = 'that_bai', 
                    ly_do_huy = %s,
                    ngay_cap_nhat = %s
                WHERE ma_don_hang = %s
            """, (request.ly_do, datetime.now(), ma_don_hang))
            conn.commit()

        return {
            "message": "Đơn hàng đã được hủy thành công",
            "ma_don_hang": ma_don_hang,
            "ly_do_huy": request.ly_do
        }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")
    
    finally:
        conn.close()

class ReviewResponse(BaseModel):
    ma_danh_gia: int
    ten_nguoi_danh_gia: Optional[str]
    hinh_anh_nguoi_danh_gia: Optional[str]
    diem_so: int
    binh_luan: Optional[str]
    hinh_anh_danh_gia: Optional[str]
    ngay_danh_gia: datetime

class ProductReviewsResponse(BaseModel):
    ten_san_pham: str
    tong_so_danh_gia: int
    diem_trung_binh: float
    danh_sach_danh_gia: List[ReviewResponse]

@app.get("/danhGia/sanPham/{ma_san_pham}")
def lay_danh_gia_san_pham(
    ma_san_pham: int,
    page: int = Query(1, ge=1, description="Số trang"),
    limit: int = Query(10, ge=1, le=50, description="Số đánh giá mỗi trang")
):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # 1. Kiểm tra sản phẩm có tồn tại không
        cursor.execute("SELECT ten_san_pham FROM SanPham WHERE ma_san_pham = %s", (ma_san_pham,))
        san_pham = cursor.fetchone()
        if not san_pham:
            raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

        ten_san_pham = san_pham[0]

        # 2. Lấy thống kê tổng quan
        cursor.execute("""
            SELECT 
                COUNT(*) as tong_so_danh_gia,
                COALESCE(AVG(diem_so), 0) as diem_trung_binh
            FROM DanhGia 
            WHERE ma_san_pham = %s
        """, (ma_san_pham,))
        thong_ke = cursor.fetchone()
        tong_so_danh_gia = thong_ke[0]
        diem_trung_binh = round(float(thong_ke[1]), 1) if thong_ke[1] else 0.0

        # 3. Tính toán phân trang
        offset = (page - 1) * limit

        # 4. Lấy danh sách đánh giá với phân trang
        cursor.execute("""
            SELECT 
                dg.ma_danh_gia,
                nd.ho_ten as ten_nguoi_danh_gia,
                nd.anh_dai_dien as hinh_anh_nguoi_danh_gia,
                dg.diem_so,
                dg.binh_luan,
                dg.hinh_anh_danh_gia,
                dg.ngay_tao as ngay_danh_gia
            FROM DanhGia dg
            INNER JOIN NguoiDung nd ON dg.ma_nguoi_dung = nd.ma_nguoi_dung
            WHERE dg.ma_san_pham = %s
            ORDER BY dg.ngay_tao DESC
            LIMIT %s OFFSET %s
        """, (ma_san_pham, limit, offset))

        danh_gia_data = cursor.fetchall()
        
        # 5. Chuyển đổi dữ liệu thành format response
        danh_sach_danh_gia = []
        for row in danh_gia_data:
            danh_gia = ReviewResponse(
                ma_danh_gia=row[0],
                ten_nguoi_danh_gia=row[1],
                hinh_anh_nguoi_danh_gia=row[2],
                diem_so=row[3],
                binh_luan=row[4],
                hinh_anh_danh_gia=row[5],
                ngay_danh_gia=row[6]
            )
            danh_sach_danh_gia.append(danh_gia)

        # 6. Trả về response
        return ProductReviewsResponse(
            ten_san_pham=ten_san_pham,
            tong_so_danh_gia=tong_so_danh_gia,
            diem_trung_binh=diem_trung_binh,
            danh_sach_danh_gia=danh_sach_danh_gia
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

# API lấy thống kê đánh giá chi tiết theo điểm số
@app.get("/danhGia/thongKe/{ma_san_pham}")
def lay_thong_ke_danh_gia(ma_san_pham: int):
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # Kiểm tra sản phẩm tồn tại
        cursor.execute("SELECT ten_san_pham FROM SanPham WHERE ma_san_pham = %s", (ma_san_pham,))
        san_pham = cursor.fetchone()
        if not san_pham:
            raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

        # Lấy thống kê phân phối điểm
        cursor.execute("""
            SELECT 
                diem_so,
                COUNT(*) as so_luong
            FROM DanhGia 
            WHERE ma_san_pham = %s
            GROUP BY diem_so
            ORDER BY diem_so DESC
        """, (ma_san_pham,))
        
        phan_phoi_diem = {}
        tong_danh_gia = 0
        tong_diem = 0
        
        for row in cursor.fetchall():
            diem = row[0]
            so_luong = row[1]
            phan_phoi_diem[diem] = so_luong
            tong_danh_gia += so_luong
            tong_diem += diem * so_luong

        # Đảm bảo có đủ 5 mức điểm
        for i in range(1, 6):
            if i not in phan_phoi_diem:
                phan_phoi_diem[i] = 0

        diem_trung_binh = round(tong_diem / tong_danh_gia, 1) if tong_danh_gia > 0 else 0.0

        return {
            "ten_san_pham": san_pham[0],
            "tong_so_danh_gia": tong_danh_gia,
            "diem_trung_binh": diem_trung_binh,
            "phan_phoi_diem": dict(sorted(phan_phoi_diem.items(), reverse=True))
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

os.makedirs("static/images/reviews", exist_ok=True)

class ReviewRequest(BaseModel):
    ma_nguoi_dung: int
    ma_san_pham: int
    ma_don_hang: int
    diem_so: int  # Từ 1 đến 5
    binh_luan: Optional[str] = None

@app.get("/test-image-upload")
def test_image_upload():
    """Trang test upload ảnh"""
    return """
    <html>
    <head><title>Test Upload Ảnh Đánh Giá</title></head>
    <body>
        <h2>Test Upload Ảnh Đánh Giá</h2>
        <form action="/danhGia" method="post" enctype="multipart/form-data">
            <p>Mã người dùng: <input type="number" name="ma_nguoi_dung" value="1018" required></p>
            <p>Mã sản phẩm: <input type="number" name="ma_san_pham" value="27" required></p>
            <p>Mã đơn hàng: <input type="number" name="ma_don_hang" value="77" required></p>
            <p>Điểm số (1-5): <input type="number" name="diem_so" min="1" max="5" value="5" required></p>
            <p>Bình luận: <input type="text" name="binh_luan" value="Pizza rất ngon!"></p>
            <p>Ảnh đánh giá: <input type="file" name="images" multiple accept="image/*"></p>
            <p><button type="submit">Gửi đánh giá</button></p>
        </form>
    </body>
    </html>
    """

@app.post("/danhGia")
async def them_danh_gia_with_upload(
    ma_nguoi_dung: int = Form(...),
    ma_san_pham: int = Form(...),
    ma_don_hang: int = Form(...),
    diem_so: int = Form(...),
    binh_luan: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[])
):
    """Tạo đánh giá và chỉ upload 1 ảnh duy nhất"""
    uploaded_image_path = None

    # 1. Upload ảnh 
    if images and images[0].filename:
        file = images[0]

        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} không phải là ảnh")

        content = await file.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Ảnh quá lớn (tối đa 5MB)")

        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "gif", "webp"]:
            raise HTTPException(status_code=400, detail="Định dạng ảnh không được hỗ trợ")

        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = f"/static/images/reviews/{unique_filename}"

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        uploaded_image_path = file_path

    # 2. Kết nối DB
    conn = db.connect_to_database()
    if not conn or isinstance(conn, Error):
        if uploaded_image_path:
            try:
                os.remove(uploaded_image_path)
            except:
                pass
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

    try:
        cursor = conn.cursor()

        # 3. Kiểm tra đơn hàng có hợp lệ
        cursor.execute("""
            SELECT trang_thai FROM DonHang
            WHERE ma_don_hang = %s AND ma_nguoi_dung = %s
        """, (ma_don_hang, ma_nguoi_dung))
        result = cursor.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng của người dùng")

        if result[0] != "hoan_thanh":
            raise HTTPException(status_code=400, detail="Chỉ có thể đánh giá đơn hàng đã hoàn thành")

        # 4. Sản phẩm có trong đơn hàng không
        cursor.execute("""
            SELECT COUNT(*) FROM mathangdonhang
            WHERE ma_don_hang = %s AND ma_san_pham = %s
        """, (ma_don_hang, ma_san_pham))
        if cursor.fetchone()[0] == 0:
            raise HTTPException(status_code=400, detail="Sản phẩm không thuộc đơn hàng này")

        # 5. Đã đánh giá chưa?
        cursor.execute("""
            SELECT COUNT(*) FROM DanhGia
            WHERE ma_don_hang = %s AND ma_san_pham = %s AND ma_nguoi_dung = %s
        """, (ma_don_hang, ma_san_pham, ma_nguoi_dung))
        if cursor.fetchone()[0] > 0:
            raise HTTPException(status_code=400, detail="Bạn đã đánh giá sản phẩm này trong đơn hàng này")

        # 6. Thêm đánh giá
        cursor.execute("""
            INSERT INTO DanhGia (
                ma_nguoi_dung, ma_san_pham, ma_don_hang,
                diem_so, binh_luan, hinh_anh_danh_gia, ngay_tao
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            ma_nguoi_dung,
            ma_san_pham,
            ma_don_hang,
            diem_so,
            binh_luan,
            uploaded_image_path,
            datetime.now()
        ))

        conn.commit()
        return {
            "message": "Đánh giá thành công",
            "hinh_anh_danh_gia": uploaded_image_path
        }

    except Exception as e:
        conn.rollback()
        if uploaded_image_path:
            try:
                os.remove(uploaded_image_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý: {str(e)}")

    finally:
        conn.close()

@app.get("/danhSachDonHang/{ma_nguoi_dung}")
def danh_sach_don_hang(ma_nguoi_dung: int):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối CSDL")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                dh.ma_don_hang,
                dh.ma_nguoi_dung,
                dh.tong_tien_san_pham,
                dh.phi_giao_hang,
                dh.giam_gia_ma_giam_gia,
                dh.giam_gia_combo,
                dh.tong_tien_cuoi_cung,
                dh.trang_thai,
                dh.phuong_thuc_thanh_toan,
                dh.trang_thai_thanh_toan,
                dh.ghi_chu,
                dh.thoi_gian_giao_du_kien,
                dh.ngay_tao,
                dh.ngay_cap_nhat,
                ttgh.ten_nguoi_nhan,
                ttgh.so_duong, ttgh.phuong_xa, ttgh.quan_huyen, ttgh.tinh_thanh_pho
            FROM DonHang dh
            LEFT JOIN ThongTinGiaoHang ttgh ON dh.ma_thong_tin_giao_hang = ttgh.ma_thong_tin_giao_hang
            WHERE dh.ma_nguoi_dung = %s
            ORDER BY dh.ngay_tao DESC
        """, (ma_nguoi_dung,))
        orders = cursor.fetchall()

        result = []
        for order in orders:
            # Lấy danh sách mặt hàng chi tiết
            cursor.execute("""
                SELECT 
                    mhdh.ma_mat_hang_don_hang,
                    mhdh.ma_don_hang,
                    mhdh.ma_san_pham,
                    mhdh.ma_combo,
                    mhdh.loai_mat_hang,
                    mhdh.so_luong,
                    mhdh.don_gia_co_ban,
                    mhdh.tong_gia_tuy_chon,
                    mhdh.thanh_tien,
                    mhdh.ghi_chu,
                    sp.ten_san_pham,
                    c.ten_combo
                FROM MatHangDonHang mhdh
                LEFT JOIN SanPham sp ON mhdh.ma_san_pham = sp.ma_san_pham
                LEFT JOIN Combo c ON mhdh.ma_combo = c.ma_combo
                WHERE mhdh.ma_don_hang = %s
            """, (order['ma_don_hang'],))
            items = cursor.fetchall()

            # SỬA: Format items đúng theo MatHangDonHang model
            item_objects = []
            for mh in items:
                item_objects.append({
                    "ma_mat_hang_don_hang": mh["ma_mat_hang_don_hang"],
                    "ma_don_hang": mh["ma_don_hang"],
                    "ma_san_pham": mh["ma_san_pham"],
                    "ma_combo": mh["ma_combo"],
                    "loai_mat_hang": mh["loai_mat_hang"],
                    "so_luong": mh["so_luong"],
                    "don_gia_co_ban": float(mh["don_gia_co_ban"]) if mh["don_gia_co_ban"] else 0.0,
                    "tong_gia_tuy_chon": float(mh["tong_gia_tuy_chon"]) if mh["tong_gia_tuy_chon"] else 0.0,
                    "thanh_tien": float(mh["thanh_tien"]) if mh["thanh_tien"] else 0.0,
                    "ghi_chu": mh["ghi_chu"],
                    "ten_san_pham": mh["ten_san_pham"],
                    "ten_combo": mh["ten_combo"]
                })

            # SỬA: Trả về đúng format Order model
            result.append({
                "ma_don_hang": order["ma_don_hang"],
                "ma_nguoi_dung": order["ma_nguoi_dung"],
                "tong_tien_san_pham": float(order["tong_tien_san_pham"]) if order["tong_tien_san_pham"] else 0.0,
                "phi_giao_hang": float(order["phi_giao_hang"]) if order["phi_giao_hang"] else 0.0,
                "giam_gia_ma_giam_gia": float(order["giam_gia_ma_giam_gia"]) if order["giam_gia_ma_giam_gia"] else 0.0,
                "giam_gia_combo": float(order["giam_gia_combo"]) if order["giam_gia_combo"] else 0.0,
                "tong_tien_cuoi_cung": float(order["tong_tien_cuoi_cung"]) if order["tong_tien_cuoi_cung"] else 0.0,
                "trang_thai": order["trang_thai"],  # <- KEY: Trả về đúng field name
                "phuong_thuc_thanh_toan": order["phuong_thuc_thanh_toan"] or "",
                "trang_thai_thanh_toan": order["trang_thai_thanh_toan"] or "",
                "ghi_chu": order["ghi_chu"],
                "thoi_gian_giao_du_kien": order["thoi_gian_giao_du_kien"].strftime("%Y-%m-%d %H:%M") if order["thoi_gian_giao_du_kien"] else None,
                "ngay_tao": order["ngay_tao"].strftime("%Y-%m-%d %H:%M") if order["ngay_tao"] else "",
                "ngay_cap_nhat": order["ngay_cap_nhat"].strftime("%Y-%m-%d %H:%M") if order["ngay_cap_nhat"] else "",
                "items": item_objects
            })

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/chiTietDonHang/{ma_don_hang}")
def get_chi_tiet_don_hang(ma_don_hang: int):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # === 1. Thông tin đơn hàng và giao hàng ===
        cursor.execute("""
            SELECT 
                dh.*,
                nd.ho_ten,
                nd.email,
                ttgh.ten_nguoi_nhan,
                ttgh.so_dien_thoai_nguoi_nhan,
                ttgh.so_duong,
                ttgh.phuong_xa,
                ttgh.quan_huyen,
                ttgh.tinh_thanh_pho,
                ttgh.ghi_chu AS ghi_chu_giao_hang,
                mgv.ma_code AS ma_giam_gia_code
            FROM DonHang dh
            LEFT JOIN NguoiDung nd ON dh.ma_nguoi_dung = nd.ma_nguoi_dung
            LEFT JOIN ThongTinGiaoHang ttgh ON dh.ma_thong_tin_giao_hang = ttgh.ma_thong_tin_giao_hang
            LEFT JOIN MaGiamGia mgv ON dh.ma_giam_gia = mgv.ma_giam_gia
            WHERE dh.ma_don_hang = %s
        """, (ma_don_hang,))
        don_hang = cursor.fetchone()

        if not don_hang:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")

        # === 2. Danh sách mặt hàng trong đơn ===
        cursor.execute("""
            SELECT 
                mhdh.*,
                sp.ten_san_pham,
                sp.hinh_anh,
                c.ten_combo,
                c.hinh_anh AS hinh_anh_combo
            FROM MatHangDonHang mhdh
            LEFT JOIN SanPham sp ON mhdh.ma_san_pham = sp.ma_san_pham
            LEFT JOIN Combo c ON mhdh.ma_combo = c.ma_combo
            WHERE mhdh.ma_don_hang = %s
        """, (ma_don_hang,))
        mat_hang_list = cursor.fetchall()

        # === 3. Lấy tùy chọn cho từng mặt hàng ===
        for mh in mat_hang_list:
            if mh["loai_mat_hang"] == "san_pham":
                cursor.execute("""
                    SELECT * FROM ChiTietTuyChonDonHang 
                    WHERE ma_mat_hang_don_hang = %s
                """, (mh['ma_mat_hang_don_hang'],))
                mh["tuy_chon"] = cursor.fetchall()

            elif mh["loai_mat_hang"] == "combo":
                cursor.execute("""
                    SELECT * FROM ChiTietComboDonHang 
                    WHERE ma_mat_hang_don_hang = %s
                """, (mh['ma_mat_hang_don_hang'],))
                chi_tiet_combo = cursor.fetchall()

                for ct in chi_tiet_combo:
                    cursor.execute("""
                        SELECT * FROM TuyChonComboDonHang 
                        WHERE ma_chi_tiet_combo_don_hang = %s
                    """, (ct['ma_chi_tiet'],))
                    ct['tuy_chon'] = cursor.fetchall()

                mh["chi_tiet_combo"] = chi_tiet_combo

        cursor.close()
        conn.close()

        # === 4. Format kết quả trả về giống format chuẩn ===
        dia_chi = ", ".join(filter(None, [
            don_hang.get("so_duong"),
            don_hang.get("phuong_xa"),
            don_hang.get("quan_huyen"),
            don_hang.get("tinh_thanh_pho")
        ]))

        return {
            "don_hang": {
                "ma_don_hang": don_hang["ma_don_hang"],
                "tong_tien_san_pham": don_hang["tong_tien_san_pham"],
                "phi_giao_hang": don_hang["phi_giao_hang"],
                "giam_gia_ma_giam_gia": don_hang.get("giam_gia_ma_giam_gia", 0),
                "tong_tien_cuoi_cung": don_hang["tong_tien_cuoi_cung"],
                "trang_thai": don_hang["trang_thai"],
                "phuong_thuc_thanh_toan": don_hang["phuong_thuc_thanh_toan"],
                "trang_thai_thanh_toan": don_hang["trang_thai_thanh_toan"],
                "ghi_chu": don_hang.get("ghi_chu"),
                "thoi_gian_giao_du_kien": don_hang.get("thoi_gian_giao_du_kien"),
                "thong_tin_giao_hang": {
                    "ten_nguoi_nhan": don_hang["ten_nguoi_nhan"],
                    "so_dien_thoai": don_hang["so_dien_thoai_nguoi_nhan"],
                    "dia_chi": dia_chi,
                    "ghi_chu": don_hang.get("ghi_chu_giao_hang")
                },
                "nguoi_dat": {
                    "ho_ten": don_hang.get("ho_ten"),
                    "email": don_hang.get("email")
                },
                "ma_giam_gia": don_hang.get("ma_giam_gia_code")
            },
            "mat_hang": mat_hang_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/tatCaDonHang")
def lay_tat_ca_don_hang():
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        cursor = conn.cursor(dictionary=True)

        # === 1. Lấy tất cả đơn hàng và thông tin giao hàng liên quan ===
        cursor.execute("""
            SELECT dh.*, tgh.ten_nguoi_nhan, tgh.so_dien_thoai_nguoi_nhan,
                   tgh.so_duong, tgh.phuong_xa, tgh.quan_huyen, tgh.tinh_thanh_pho
            FROM DonHang dh
            JOIN ThongTinGiaoHang tgh ON dh.ma_thong_tin_giao_hang = tgh.ma_thong_tin_giao_hang
            ORDER BY dh.ma_don_hang DESC
        """)
        don_hang_list = cursor.fetchall()

        ket_qua = []
        for dh in don_hang_list:
            dia_chi = ", ".join(filter(None, [
                dh.get("so_duong"), dh.get("phuong_xa"),
                dh.get("quan_huyen"), dh.get("tinh_thanh_pho")
            ]))

            ket_qua.append({
                "message": "Lấy đơn hàng thành công",
                "ma_don_hang": dh["ma_don_hang"],
                "tong_tien_san_pham": dh["tong_tien_san_pham"],
                "phi_giao_hang": dh["phi_giao_hang"],
                "giam_gia_ma_giam_gia": dh.get("giam_gia_ma_giam_gia", 0),
                "tong_tien_cuoi_cung": dh["tong_tien_cuoi_cung"],
                "thoi_gian_giao_du_kien": dh.get("thoi_gian_giao_du_kien"),
                "phuong_thuc_thanh_toan": dh["phuong_thuc_thanh_toan"],
                "ghi_chu": dh.get("ghi_chu"),
                "trang_thai": dh["trang_thai"],
                "trang_thai_thanh_toan": dh["trang_thai_thanh_toan"],
                "thong_tin_giao_hang": {
                    "ten_nguoi_nhan": dh["ten_nguoi_nhan"],
                    "so_dien_thoai": dh["so_dien_thoai_nguoi_nhan"],
                    "dia_chi": dia_chi
                }
            })

        return {"don_hang": ket_qua}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

class TrangThaiEnum(str, Enum):
    HOAT_DONG = "hoat_dong"
    KHONG_DUNG = "khong_dung"

class ThongTinGiaoHangCreate(BaseModel):
    ten_nguoi_nhan: str
    so_dien_thoai_nguoi_nhan: str
    so_duong: str
    phuong_xa: Optional[str] = None
    quan_huyen: Optional[str] = None
    tinh_thanh_pho: Optional[str] = None
    la_dia_chi_mac_dinh: bool = False
    ghi_chu: Optional[str] = None
    trang_thai: TrangThaiEnum = TrangThaiEnum.HOAT_DONG

class ThongTinGiaoHangResponse(BaseModel):
    ma_thong_tin_giao_hang: int
    ma_nguoi_dung: int
    ten_nguoi_nhan: str
    so_dien_thoai_nguoi_nhan: str
    so_duong: str
    phuong_xa: Optional[str]
    quan_huyen: Optional[str]
    tinh_thanh_pho: Optional[str]
    la_dia_chi_mac_dinh: bool
    ghi_chu: Optional[str]
    trang_thai: TrangThaiEnum
    ngay_tao: str
    ngay_cap_nhat: str

@app.post("/users/{ma_nguoi_dung}/delivery-addresses")
def create_delivery_address(
    ma_nguoi_dung: int, 
    address_data: ThongTinGiaoHangCreate
):
    """
    Thêm địa chỉ giao hàng mới cho người dùng
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra người dùng có tồn tại không
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Người dùng không tồn tại"
            )
        
        # Nếu đây là địa chỉ mặc định, bỏ mặc định các địa chỉ khác
        if address_data.la_dia_chi_mac_dinh:
            cursor.execute(
                "UPDATE ThongTinGiaoHang SET la_dia_chi_mac_dinh = FALSE WHERE ma_nguoi_dung = %s",
                (ma_nguoi_dung,)
            )
        
        # Thêm địa chỉ mới (bao gồm cột trang_thai)
        insert_query = """
        INSERT INTO ThongTinGiaoHang 
        (ma_nguoi_dung, ten_nguoi_nhan, so_dien_thoai_nguoi_nhan, so_duong, 
         phuong_xa, quan_huyen, tinh_thanh_pho, la_dia_chi_mac_dinh, ghi_chu, trang_thai)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            ma_nguoi_dung,
            address_data.ten_nguoi_nhan,
            address_data.so_dien_thoai_nguoi_nhan,
            address_data.so_duong,
            address_data.phuong_xa,
            address_data.quan_huyen,
            address_data.tinh_thanh_pho,
            address_data.la_dia_chi_mac_dinh,
            address_data.ghi_chu,
            address_data.trang_thai.value
        ))
        
        address_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "message": "Thêm địa chỉ giao hàng thành công",
            "data": {
                "ma_thong_tin_giao_hang": address_id,
                "ma_nguoi_dung": ma_nguoi_dung
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating delivery address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/users/{ma_nguoi_dung}/delivery-addresses")
def get_delivery_addresses(ma_nguoi_dung: int, chi_lay_hoat_dong: bool = True):
    """
    Lấy danh sách địa chỉ giao hàng của người dùng
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra người dùng có tồn tại không
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Người dùng không tồn tại"
            )
        
        # Lấy danh sách địa chỉ (có thể lọc theo trạng thái)
        if chi_lay_hoat_dong:
            cursor.execute("""
                SELECT * FROM ThongTinGiaoHang 
                WHERE ma_nguoi_dung = %s AND trang_thai = 'hoat_dong'
                ORDER BY la_dia_chi_mac_dinh DESC, ngay_cap_nhat DESC
            """, (ma_nguoi_dung,))
        else:
            cursor.execute("""
                SELECT * FROM ThongTinGiaoHang 
                WHERE ma_nguoi_dung = %s 
                ORDER BY la_dia_chi_mac_dinh DESC, ngay_cap_nhat DESC
            """, (ma_nguoi_dung,))
        
        addresses = cursor.fetchall()
        
        return {
            "success": True,
            "message": "Lấy danh sách địa chỉ thành công",
            "data": addresses,
            "total": len(addresses)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delivery addresses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.get("/users/{ma_nguoi_dung}/delivery-addresses/{ma_thong_tin_giao_hang}")
def get_delivery_address_detail(ma_nguoi_dung: int, ma_thong_tin_giao_hang: int):
    """
    Lấy chi tiết một địa chỉ giao hàng
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        address = cursor.fetchone()
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa chỉ giao hàng"
            )
        
        return {
            "success": True,
            "message": "Lấy thông tin địa chỉ thành công",
            "data": address
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting delivery address detail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

class ThongTinGiaoHangUpdate(BaseModel):
    ten_nguoi_nhan: Optional[str] = None
    so_dien_thoai_nguoi_nhan: Optional[str] = None
    so_duong: Optional[str] = None
    phuong_xa: Optional[str] = None
    quan_huyen: Optional[str] = None
    tinh_thanh_pho: Optional[str] = None
    la_dia_chi_mac_dinh: Optional[bool] = None
    ghi_chu: Optional[str] = None
    trang_thai: Optional[TrangThaiEnum] = None

@app.put("/users/{ma_nguoi_dung}/delivery-addresses/{ma_thong_tin_giao_hang}")
def update_delivery_address(
    ma_nguoi_dung: int, 
    ma_thong_tin_giao_hang: int,
    address_data: ThongTinGiaoHangUpdate
):
    """
    Cập nhật thông tin địa chỉ giao hàng
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra địa chỉ có tồn tại và thuộc về người dùng không
        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        existing_address = cursor.fetchone()
        if not existing_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa chỉ giao hàng"
            )
        
        # Tạo dictionary với các giá trị cần cập nhật
        update_fields = {}
        update_values = []
        
        if address_data.ten_nguoi_nhan is not None:
            update_fields['ten_nguoi_nhan'] = '%s'
            update_values.append(address_data.ten_nguoi_nhan)
            
        if address_data.so_dien_thoai_nguoi_nhan is not None:
            update_fields['so_dien_thoai_nguoi_nhan'] = '%s'
            update_values.append(address_data.so_dien_thoai_nguoi_nhan)
            
        if address_data.so_duong is not None:
            update_fields['so_duong'] = '%s'
            update_values.append(address_data.so_duong)
            
        if address_data.phuong_xa is not None:
            update_fields['phuong_xa'] = '%s'
            update_values.append(address_data.phuong_xa)
            
        if address_data.quan_huyen is not None:
            update_fields['quan_huyen'] = '%s'
            update_values.append(address_data.quan_huyen)
            
        if address_data.tinh_thanh_pho is not None:
            update_fields['tinh_thanh_pho'] = '%s'
            update_values.append(address_data.tinh_thanh_pho)
            
        if address_data.ghi_chu is not None:
            update_fields['ghi_chu'] = '%s'
            update_values.append(address_data.ghi_chu)
            
        if address_data.trang_thai is not None:
            update_fields['trang_thai'] = '%s'
            update_values.append(address_data.trang_thai.value)
            
        if address_data.la_dia_chi_mac_dinh is not None:
            update_fields['la_dia_chi_mac_dinh'] = '%s'
            update_values.append(address_data.la_dia_chi_mac_dinh)
            
            # Nếu đặt làm mặc định, bỏ mặc định các địa chỉ khác
            if address_data.la_dia_chi_mac_dinh:
                cursor.execute(
                    "UPDATE ThongTinGiaoHang SET la_dia_chi_mac_dinh = FALSE WHERE ma_nguoi_dung = %s AND ma_thong_tin_giao_hang != %s",
                    (ma_nguoi_dung, ma_thong_tin_giao_hang)
                )
        
        if not update_fields:
            return {
                "success": True,
                "message": "Không có thông tin nào được cập nhật",
                "data": existing_address
            }
        
        # Tạo câu lệnh UPDATE
        set_clause = ', '.join([f"{field} = {placeholder}" for field, placeholder in update_fields.items()])
        update_query = f"UPDATE ThongTinGiaoHang SET {set_clause} WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s"
        update_values.extend([ma_thong_tin_giao_hang, ma_nguoi_dung])
        
        cursor.execute(update_query, update_values)
        conn.commit()
        
        # Lấy thông tin địa chỉ sau khi cập nhật
        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        updated_address = cursor.fetchone()
        
        return {
            "success": True,
            "message": "Cập nhật địa chỉ giao hàng thành công",
            "data": updated_address
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating delivery address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.delete("/users/{ma_nguoi_dung}/delivery-addresses/{ma_thong_tin_giao_hang}")
def delete_delivery_address(ma_nguoi_dung: int, ma_thong_tin_giao_hang: int):
    """
    Xóa địa chỉ giao hàng (soft delete - chuyển trạng thái thành 'khong_dung')
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra địa chỉ có tồn tại và thuộc về người dùng không
        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        address = cursor.fetchone()
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa chỉ giao hàng"
            )
        
        # Kiểm tra xem địa chỉ đã ở trạng thái 'khong_dung' chưa
        if address['trang_thai'] == TrangThaiEnum.KHONG_DUNG:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Địa chỉ giao hàng đã được xóa trước đó"
            )
        
        # Luôn thực hiện soft delete - chuyển trạng thái thành 'khong_dung'
        cursor.execute("""
            UPDATE ThongTinGiaoHang 
            SET trang_thai = %s, la_dia_chi_mac_dinh = FALSE, ngay_cap_nhat = NOW()
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (TrangThaiEnum.KHONG_DUNG, ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        conn.commit()
        
        # Nếu xóa địa chỉ mặc định, đặt địa chỉ khác làm mặc định (nếu có)
        if address['la_dia_chi_mac_dinh']:
            cursor.execute("""
                SELECT ma_thong_tin_giao_hang FROM ThongTinGiaoHang 
                WHERE ma_nguoi_dung = %s AND trang_thai = %s
                ORDER BY ngay_cap_nhat DESC 
                LIMIT 1
            """, (ma_nguoi_dung, TrangThaiEnum.HOAT_DONG))
            
            next_default = cursor.fetchone()
            if next_default:
                cursor.execute("""
                    UPDATE ThongTinGiaoHang 
                    SET la_dia_chi_mac_dinh = TRUE, ngay_cap_nhat = NOW()
                    WHERE ma_thong_tin_giao_hang = %s
                """, (next_default['ma_thong_tin_giao_hang'],))
                conn.commit()
        
        return {
            "success": True,
            "message": "Xóa địa chỉ giao hàng thành công",
            "data": {
                "ma_thong_tin_giao_hang": ma_thong_tin_giao_hang,
                "ma_nguoi_dung": ma_nguoi_dung,
                "trang_thai": TrangThaiEnum.KHONG_DUNG
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting delivery address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.patch("/users/{ma_nguoi_dung}/delivery-addresses/{ma_thong_tin_giao_hang}/set-default")
def set_default_delivery_address(ma_nguoi_dung: int, ma_thong_tin_giao_hang: int):
    """
    Đặt địa chỉ giao hàng làm mặc định (chỉ với địa chỉ đang hoạt động)
    """
    conn = None
    cursor = None
    
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)
        
        # Kiểm tra địa chỉ có tồn tại, thuộc về người dùng và đang hoạt động không
        cursor.execute("""
            SELECT * FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s AND trang_thai = 'hoat_dong'
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        address = cursor.fetchone()
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy địa chỉ giao hàng hoạt động"
            )
        
        # Bỏ mặc định tất cả địa chỉ khác
        cursor.execute("""
            UPDATE ThongTinGiaoHang 
            SET la_dia_chi_mac_dinh = FALSE 
            WHERE ma_nguoi_dung = %s
        """, (ma_nguoi_dung,))
        
        # Đặt địa chỉ này làm mặc định
        cursor.execute("""
            UPDATE ThongTinGiaoHang 
            SET la_dia_chi_mac_dinh = TRUE 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Đặt địa chỉ mặc định thành công",
            "data": {
                "ma_thong_tin_giao_hang": ma_thong_tin_giao_hang,
                "ma_nguoi_dung": ma_nguoi_dung
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default delivery address: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi server nội bộ"
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


conf = ConnectionConfig(
    MAIL_USERNAME="vviethhoang@gmail.com",
    MAIL_PASSWORD="svmf gjrv lwft yvqr",
    MAIL_FROM="vviethhoang@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

def generate_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))

def generate_activation_token():
    """Tạo token để kích hoạt mật khẩu mới"""
    return secrets.token_urlsafe(32)

async def send_email_with_password_and_link(to_email: str, new_password: str, activation_token: str):
    # URL để kích hoạt mật khẩu
    activation_url = f"{urlApp}/kich-hoat-mat-khau?token={activation_token}"
    
    message = MessageSchema(
        subject="Mật khẩu mới từ Pizza App - Cần kích hoạt",
        recipients=[to_email],
        body=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">Pizza App - Mật khẩu mới</h2>
                <p>Chào bạn,</p>
                <p>Mật khẩu mới của bạn là:</p>
                
                <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <h3 style="color: #d32f2f; margin: 0;">{new_password}</h3>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <strong>⚠️ Quan trọng:</strong> Mật khẩu này chưa có hiệu lực. 
                    Bạn cần nhấn vào nút bên dưới để kích hoạt mật khẩu mới.
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{activation_url}" 
                       style="background-color: #28a745; color: white; padding: 15px 30px; 
                              text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Kích hoạt mật khẩu mới
                    </a>
                </div>
                
                <p>Hoặc copy link sau vào trình duyệt của bạn:</p>
                <p style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all;">
                    {activation_url}
                </p>
                
                <p><strong>Lưu ý:</strong></p>
                <ul>
                    <li>Link kích hoạt này chỉ có hiệu lực trong vòng 24 giờ</li>
                    <li>Sau khi kích hoạt, bạn có thể đăng nhập bằng mật khẩu mới</li>
                    <li>Mật khẩu cũ vẫn có hiệu lực cho đến khi bạn kích hoạt mật khẩu mới</li>
                </ul>
                
                <p>Trân trọng,<br>
                <strong>Pizza App Team</strong></p>
            </div>
        """,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

@app.post("/quen-mat-khau")
async def quen_mat_khau(email: EmailStr = Form(...)):
    conn = db.connect_to_database()
    cursor = conn.cursor(dictionary=True)

    # Kiểm tra email có tồn tại không
    cursor.execute("SELECT * FROM NguoiDung WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại")

    # Tạo mật khẩu mới và token kích hoạt
    new_password = generate_password()
    activation_token = generate_activation_token()
    expires_at = datetime.now() + timedelta(hours=24)  # Token có hiệu lực 24 giờ

    # Lưu thông tin vào bảng pending_password_changes
    cursor.execute("""
        INSERT INTO pending_password_changes (email, new_password, activation_token, expires_at, created_at, activated) 
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        new_password = VALUES(new_password),
        activation_token = VALUES(activation_token), 
        expires_at = VALUES(expires_at), 
        created_at = VALUES(created_at),
        activated = 0
    """, (email, new_password, activation_token, expires_at, datetime.now(), False))
    
    conn.commit()

    # Gửi email với mật khẩu mới và link kích hoạt
    await send_email_with_password_and_link(email, new_password, activation_token)

    return {"message": "Mật khẩu mới đã được gửi về email của bạn. Vui lòng kiểm tra email và nhấn link để kích hoạt mật khẩu."}

@app.get("/kich-hoat-mat-khau")
async def kich_hoat_mat_khau(token: str):
    conn = db.connect_to_database()
    cursor = conn.cursor(dictionary=True)

    try:
        # Kiểm tra token có hợp lệ không
        cursor.execute("""
            SELECT * FROM pending_password_changes 
            WHERE activation_token = %s AND expires_at > %s AND activated = 0
        """, (token, datetime.now()))
        
        pending_change = cursor.fetchone()
        if not pending_change:
            # Token không hợp lệ hoặc đã hết hạn
            return HTMLResponse(content="""
            <!DOCTYPE html>
            <html lang="vi">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Kích hoạt thất bại - Pizza App</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }
                    .container {
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        max-width: 400px;
                        width: 100%;
                        text-align: center;
                    }
                    h1 {
                        color: #d32f2f;
                        font-size: 24px;
                        margin-bottom: 15px;
                    }
                    p {
                        color: #666;
                        font-size: 16px;
                        line-height: 1.5;
                        margin-bottom: 20px;
                    }
                    .btn {
                        background-color: #d32f2f;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 4px;
                        font-size: 16px;
                        cursor: pointer;
                        text-decoration: none;
                        display: inline-block;
                    }
                    .btn:hover {
                        background-color: #b71c1c;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Kích hoạt thất bại</h1>
                    <p>Link kích hoạt không hợp lệ hoặc đã hết hạn.<br>Vui lòng yêu cầu đặt lại mật khẩu mới.</p>
                </div>
            </body>
            </html>
            """, status_code=400)

        # Cập nhật mật khẩu trong bảng NguoiDung
        cursor.execute("UPDATE NguoiDung SET mat_khau = %s WHERE email = %s", 
                       (pending_change['new_password'], pending_change['email']))
        
        # Đánh dấu đã kích hoạt
        cursor.execute("UPDATE pending_password_changes SET activated = 1 WHERE activation_token = %s", (token,))
        
        conn.commit()

        # Trả về trang thành công
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Kích hoạt thành công - Pizza KimChi</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                }
                h1 {
                    color: #2e7d32;
                    font-size: 24px;
                    margin-bottom: 15px;
                }
                p {
                    color: #666;
                    font-size: 16px;
                    line-height: 1.5;
                    margin-bottom: 20px;
                }
                .info-box {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    border-left: 4px solid #2e7d32;
                }
                .btn {
                    background-color: #2e7d32;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    margin: 5px;
                }
                .btn:hover {
                    background-color: #1b5e20;
                }
                .btn-secondary {
                    background-color: #757575;
                }
                .btn-secondary:hover {
                    background-color: #616161;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Kích hoạt thành công!</h1>
                <p>Mật khẩu của bạn đã được kích hoạt thành công.<br>Bạn có thể đăng nhập bằng mật khẩu mới ngay bây giờ.</p>
                
                <div class="info-box">
                    <strong>🔐 Mật khẩu mới đã có hiệu lực</strong><br>
                    <small>Hãy đăng nhập và đổi lại mật khẩu nếu cần thiết</small>
                </div>
                
            </div>
        </body>
        </html>
        """)
        
    except Exception as e:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lỗi - Pizza App</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    max-width: 400px;
                    width: 100%;
                    text-align: center;
                }
                h1 {
                    color: #d32f2f;
                    font-size: 24px;
                    margin-bottom: 15px;
                }
                p {
                    color: #666;
                    font-size: 16px;
                    line-height: 1.5;
                    margin-bottom: 20px;
                }
                .btn {
                    background-color: #d32f2f;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                }
                .btn:hover {
                    background-color: #b71c1c;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Có lỗi xảy ra</h1>
                <p>Đã có lỗi trong quá trình kích hoạt mật khẩu.<br>Vui lòng thử lại sau.</p>
                <a href="#" class="btn" onclick="window.close()">Đóng</a>
            </div>
        </body>
        </html>
        """, status_code=500)

# API để kiểm tra trạng thái token
@app.get("/check-activation-token/{token}")
async def check_activation_token(token: str):
    conn = db.connect_to_database()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT email, created_at, expires_at, activated FROM pending_password_changes 
        WHERE activation_token = %s
    """, (token,))
    
    record = cursor.fetchone()
    if not record:
        return {"valid": False, "message": "Token không tồn tại"}
    
    if record['activated']:
        return {"valid": False, "message": "Mật khẩu đã được kích hoạt trước đó"}
    
    if datetime.now() > record['expires_at']:
        return {"valid": False, "message": "Link đã hết hạn"}
    
    return {
        "valid": True, 
        "email": record['email'],
        "expires_at": record['expires_at'].isoformat()
    }

class TuyChonRequest(BaseModel):
    ma_gia_tri: int
    gia_them: float

class ChiTietComboRequest(BaseModel):
    ma_chi_tiet_combo: int
    tuy_chon: Optional[List[TuyChonRequest]] = []

class ThemVaoGioHangRequest(BaseModel):
    ma_nguoi_dung: int
    ma_san_pham: Optional[int] = None
    ma_combo: Optional[int] = None
    loai_mat_hang: str  # 'san_pham' hoặc 'combo'
    so_luong: int
    ghi_chu: Optional[str] = None
    tuy_chon: Optional[List[TuyChonRequest]] = []  # Cho sản phẩm đơn lẻ
    chi_tiet_combo: Optional[List[ChiTietComboRequest]] = []  # Cho combo

@app.get("/layGioHang/{ma_nguoi_dung}")
def get_gio_hang(ma_nguoi_dung: int):
    """Lấy toàn bộ giỏ hàng của người dùng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # Lấy thông tin giỏ hàng
        cursor.execute("""
            SELECT gh.ma_gio_hang, gh.ngay_tao
            FROM GioHang gh 
            WHERE gh.ma_nguoi_dung = %s
        """, (ma_nguoi_dung,))
        
        gio_hang = cursor.fetchone()
        
        if not gio_hang:
            # Tạo giỏ hàng mới nếu chưa có
            cursor.execute("""
                INSERT INTO GioHang (ma_nguoi_dung) VALUES (%s)
            """, (ma_nguoi_dung,))
            ma_gio_hang = cursor.lastrowid
            conn.commit()
            
            cursor.close()
            conn.close()
            return {
                "ma_gio_hang": ma_gio_hang,
                "ma_nguoi_dung": ma_nguoi_dung,
                "mat_hang": [],
                "tong_tien": 0
            }

        # Lấy các mặt hàng trong giỏ
        cursor.execute("""
            SELECT 
                mhgh.ma_mat_hang_gio_hang,
                mhgh.ma_san_pham,
                mhgh.ma_combo,
                mhgh.loai_mat_hang,
                mhgh.so_luong,
                mhgh.gia_san_pham,
                mhgh.ghi_chu,
                sp.ten_san_pham,
                sp.hinh_anh,
                c.ten_combo,
                c.hinh_anh as hinh_anh_combo
            FROM MatHangGioHang mhgh
            LEFT JOIN SanPham sp ON mhgh.ma_san_pham = sp.ma_san_pham
            LEFT JOIN Combo c ON mhgh.ma_combo = c.ma_combo
            WHERE mhgh.ma_gio_hang = %s
        """, (gio_hang['ma_gio_hang'],))
        
        mat_hang_list = cursor.fetchall()
        tong_tien = 0

        for mat_hang in mat_hang_list:
            # Lấy tùy chọn cho sản phẩm đơn lẻ
            if mat_hang['loai_mat_hang'] == 'san_pham':
                cursor.execute("""
                    SELECT 
                        cttcgh.ma_gia_tri,
                        cttcgh.gia_them,
                        gtc.ten_gia_tri,
                        ltc.ten_loai
                    FROM ChiTietTuyChonGioHang cttcgh
                    JOIN GiaTriTuyChon gtc ON cttcgh.ma_gia_tri = gtc.ma_gia_tri
                    JOIN LoaiTuyChon ltc ON gtc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
                    WHERE cttcgh.ma_mat_hang_gio_hang = %s
                """, (mat_hang['ma_mat_hang_gio_hang'],))
                
                mat_hang['tuy_chon'] = cursor.fetchall()
                tong_gia_tuy_chon = sum(tc['gia_them'] for tc in mat_hang['tuy_chon'])
                mat_hang['thanh_tien'] = (mat_hang['gia_san_pham'] + tong_gia_tuy_chon) * mat_hang['so_luong']
                
            # Lấy chi tiết combo
            elif mat_hang['loai_mat_hang'] == 'combo':
                cursor.execute("""
                    SELECT 
                        ctcgh.ma_chi_tiet,
                        ctcgh.ma_chi_tiet_combo,
                        ctc.ma_san_pham,
                        ctc.ten_san_pham,
                        ctc.so_luong as so_luong_combo,
                        ctc.gia_san_pham
                    FROM ChiTietComboGioHang ctcgh
                    JOIN ChiTietCombo ctc ON ctcgh.ma_chi_tiet_combo = ctc.ma_chi_tiet_combo
                    WHERE ctcgh.ma_mat_hang_gio_hang = %s
                """, (mat_hang['ma_mat_hang_gio_hang'],))
                
                chi_tiet_combo = cursor.fetchall()
                
                # Lấy tùy chọn cho từng sản phẩm trong combo
                for ct in chi_tiet_combo:
                    cursor.execute("""
                        SELECT 
                            tccgh.ma_gia_tri,
                            tccgh.gia_them,
                            gtc.ten_gia_tri,
                            ltc.ten_loai
                        FROM TuyChonComboGioHang tccgh
                        JOIN GiaTriTuyChon gtc ON tccgh.ma_gia_tri = gtc.ma_gia_tri
                        JOIN LoaiTuyChon ltc ON gtc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
                        WHERE tccgh.ma_chi_tiet_combo_gio_hang = %s
                    """, (ct['ma_chi_tiet'],))
                    
                    ct['tuy_chon'] = cursor.fetchall()
                
                mat_hang['chi_tiet_combo'] = chi_tiet_combo
                mat_hang['thanh_tien'] = mat_hang['gia_san_pham'] * mat_hang['so_luong']
            
            tong_tien += mat_hang['thanh_tien']

        cursor.close()
        conn.close()

        return {
            "ma_gio_hang": gio_hang['ma_gio_hang'],
            "ma_nguoi_dung": ma_nguoi_dung,
            "ngay_tao": gio_hang['ngay_tao'],
            "mat_hang": mat_hang_list,
            "tong_tien": tong_tien
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/themVaoGioHang")
def them_vao_gio_hang(request: ThemVaoGioHangRequest):
    """Thêm sản phẩm hoặc combo vào giỏ hàng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra người dùng tồn tại
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", 
                      (request.ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

        # Tạo hoặc lấy giỏ hàng
        cursor.execute("SELECT ma_gio_hang FROM GioHang WHERE ma_nguoi_dung = %s", 
                      (request.ma_nguoi_dung,))
        gio_hang = cursor.fetchone()
        
        if not gio_hang:
            cursor.execute("INSERT INTO GioHang (ma_nguoi_dung) VALUES (%s)", 
                          (request.ma_nguoi_dung,))
            ma_gio_hang = cursor.lastrowid
        else:
            ma_gio_hang = gio_hang[0]

        # Lấy giá sản phẩm/combo
        if request.loai_mat_hang == 'san_pham':
            cursor.execute("SELECT gia_co_ban FROM SanPham WHERE ma_san_pham = %s", 
                          (request.ma_san_pham,))
            san_pham = cursor.fetchone()
            if not san_pham:
                raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")
            gia_san_pham = san_pham[0]
        else:
            cursor.execute("SELECT gia_ban FROM Combo WHERE ma_combo = %s", 
                          (request.ma_combo,))
            combo = cursor.fetchone()
            if not combo:
                raise HTTPException(status_code=404, detail="Combo không tồn tại")
            gia_san_pham = combo[0]

        # Thêm mặt hàng vào giỏ
        cursor.execute("""
            INSERT INTO MatHangGioHang 
            (ma_gio_hang, ma_san_pham, ma_combo, loai_mat_hang, so_luong, gia_san_pham, ghi_chu)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (ma_gio_hang, request.ma_san_pham, request.ma_combo, 
              request.loai_mat_hang, request.so_luong, gia_san_pham, request.ghi_chu))
        
        ma_mat_hang_gio_hang = cursor.lastrowid

        # Thêm tùy chọn cho sản phẩm đơn lẻ
        if request.loai_mat_hang == 'san_pham' and request.tuy_chon:
            for tuy_chon in request.tuy_chon:
                cursor.execute("""
                    INSERT INTO ChiTietTuyChonGioHang 
                    (ma_mat_hang_gio_hang, ma_gia_tri, gia_them)
                    VALUES (%s, %s, %s)
                """, (ma_mat_hang_gio_hang, tuy_chon.ma_gia_tri, tuy_chon.gia_them))

        # Thêm chi tiết combo
        if request.loai_mat_hang == 'combo' and request.chi_tiet_combo:
            for chi_tiet in request.chi_tiet_combo:
                cursor.execute("""
                    INSERT INTO ChiTietComboGioHang 
                    (ma_mat_hang_gio_hang, ma_chi_tiet_combo)
                    VALUES (%s, %s)
                """, (ma_mat_hang_gio_hang, chi_tiet.ma_chi_tiet_combo))
                
                ma_chi_tiet_combo_gio_hang = cursor.lastrowid
                
                # Thêm tùy chọn cho từng sản phẩm trong combo
                for tuy_chon in chi_tiet.tuy_chon:
                    cursor.execute("""
                        INSERT INTO TuyChonComboGioHang 
                        (ma_chi_tiet_combo_gio_hang, ma_gia_tri, gia_them)
                        VALUES (%s, %s, %s)
                    """, (ma_chi_tiet_combo_gio_hang, tuy_chon.ma_gia_tri, tuy_chon.gia_them))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "message": "Đã thêm vào giỏ hàng thành công",
            "ma_mat_hang_gio_hang": ma_mat_hang_gio_hang
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

class CapNhatGioHangRequest(BaseModel):
        so_luong: int
        ghi_chu: Optional[str] = None
        tuy_chon: Optional[List[TuyChonRequest]] = []
        chi_tiet_combo: Optional[List[ChiTietComboRequest]] = []

@app.put("/capNhatGioHang/{ma_mat_hang_gio_hang}")
def cap_nhat_gio_hang(ma_mat_hang_gio_hang: int, request: CapNhatGioHangRequest):
    """Cập nhật mặt hàng trong giỏ hàng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra mặt hàng tồn tại
        cursor.execute("""
            SELECT loai_mat_hang FROM MatHangGioHang 
            WHERE ma_mat_hang_gio_hang = %s
        """, (ma_mat_hang_gio_hang,))
        
        mat_hang = cursor.fetchone()
        if not mat_hang:
            raise HTTPException(status_code=404, detail="Mặt hàng không tồn tại trong giỏ hàng")

        loai_mat_hang = mat_hang[0]

        # Cập nhật thông tin cơ bản
        cursor.execute("""
            UPDATE MatHangGioHang 
            SET so_luong = %s, ghi_chu = %s
            WHERE ma_mat_hang_gio_hang = %s
        """, (request.so_luong, request.ghi_chu, ma_mat_hang_gio_hang))

        # Cập nhật tùy chọn cho sản phẩm đơn lẻ
        if loai_mat_hang == 'san_pham':
            # Xóa tùy chọn cũ
            cursor.execute("""
                DELETE FROM ChiTietTuyChonGioHang 
                WHERE ma_mat_hang_gio_hang = %s
            """, (ma_mat_hang_gio_hang,))
            
            # Thêm tùy chọn mới
            for tuy_chon in request.tuy_chon:
                cursor.execute("""
                    INSERT INTO ChiTietTuyChonGioHang 
                    (ma_mat_hang_gio_hang, ma_gia_tri, gia_them)
                    VALUES (%s, %s, %s)
                """, (ma_mat_hang_gio_hang, tuy_chon.ma_gia_tri, tuy_chon.gia_them))

        # Cập nhật tùy chọn cho combo
        elif loai_mat_hang == 'combo':
            # Xóa tùy chọn combo cũ
            cursor.execute("""
                DELETE tccgh FROM TuyChonComboGioHang tccgh
                JOIN ChiTietComboGioHang ctcgh ON tccgh.ma_chi_tiet_combo_gio_hang = ctcgh.ma_chi_tiet
                WHERE ctcgh.ma_mat_hang_gio_hang = %s
            """, (ma_mat_hang_gio_hang,))
            
            # Thêm tùy chọn combo mới
            for chi_tiet in request.chi_tiet_combo:
                # Lấy ma_chi_tiet từ ChiTietComboGioHang
                cursor.execute("""
                    SELECT ma_chi_tiet FROM ChiTietComboGioHang 
                    WHERE ma_mat_hang_gio_hang = %s AND ma_chi_tiet_combo = %s
                """, (ma_mat_hang_gio_hang, chi_tiet.ma_chi_tiet_combo))
                
                chi_tiet_result = cursor.fetchone()
                if chi_tiet_result:
                    ma_chi_tiet_combo_gio_hang = chi_tiet_result[0]
                    
                    for tuy_chon in chi_tiet.tuy_chon:
                        cursor.execute("""
                            INSERT INTO TuyChonComboGioHang 
                            (ma_chi_tiet_combo_gio_hang, ma_gia_tri, gia_them)
                            VALUES (%s, %s, %s)
                        """, (ma_chi_tiet_combo_gio_hang, tuy_chon.ma_gia_tri, tuy_chon.gia_them))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Đã cập nhật giỏ hàng thành công"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.delete("/xoaKhoiGioHang/{ma_mat_hang_gio_hang}")
def xoa_khoi_gio_hang(ma_mat_hang_gio_hang: int):
    """Xóa mặt hàng khỏi giỏ hàng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra mặt hàng tồn tại
        cursor.execute("""
            SELECT ma_mat_hang_gio_hang FROM MatHangGioHang 
            WHERE ma_mat_hang_gio_hang = %s
        """, (ma_mat_hang_gio_hang,))
        
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Mặt hàng không tồn tại trong giỏ hàng")

        # Xóa mặt hàng (CASCADE sẽ tự động xóa các bảng liên quan)
        cursor.execute("""
            DELETE FROM MatHangGioHang 
            WHERE ma_mat_hang_gio_hang = %s
        """, (ma_mat_hang_gio_hang,))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": f"Đã xóa mặt hàng {ma_mat_hang_gio_hang} khỏi giỏ hàng thành công"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.delete("/xoaToanBoGioHang/{ma_nguoi_dung}")
def xoa_toan_bo_gio_hang(ma_nguoi_dung: int):
    """Xóa toàn bộ giỏ hàng của người dùng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra người dùng tồn tại
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", 
                      (ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

        # Lấy mã giỏ hàng
        cursor.execute("SELECT ma_gio_hang FROM GioHang WHERE ma_nguoi_dung = %s", 
                      (ma_nguoi_dung,))
        gio_hang = cursor.fetchone()
        
        if not gio_hang:
            return {"message": "Giỏ hàng đã trống"}

        # Xóa tất cả mặt hàng trong giỏ
        cursor.execute("""
            DELETE FROM MatHangGioHang 
            WHERE ma_gio_hang = %s
        """, (gio_hang[0],))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Đã xóa toàn bộ giỏ hàng thành công"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.delete("/xoaNguoiDung/{ma_nguoi_dung}")
def delete_nguoi_dung(ma_nguoi_dung: int):
    try:
        # Kết nối CSDL
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra người dùng có tồn tại không
        cursor.execute("SELECT * FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

        # Thực hiện xóa
        cursor.execute("DELETE FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "message": f"Đã xóa người dùng có mã {ma_nguoi_dung} thành công"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/getAllNguoiDung")
def get_all_nguoi_dung():
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM NguoiDung")
        users = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "message": "Lấy danh sách người dùng thành công",
            "data": users,
            "total": len(users)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/dang-ky")
def dang_ky_tai_khoan(
    email: str = Form(...),
    so_dien_thoai: Optional[str] = Form(None),
    mat_khau: str = Form(...),
    ho_ten: Optional[str] = Form(None)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        cursor = conn.cursor()

        # ✅ Kiểm tra email đã tồn tại
        cursor.execute("SELECT * FROM NguoiDung WHERE email = %s", (email,))
        if cursor.fetchone():
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "Email đã được sử dụng",
                    "user": None
                }
            )

        if so_dien_thoai:
            cursor.execute("SELECT * FROM NguoiDung WHERE so_dien_thoai = %s", (so_dien_thoai,))
            if cursor.fetchone():
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "message": "Số điện thoại đã được sử dụng",
                        "user": None
                    }
                )

        sql = """
            INSERT INTO NguoiDung (email, so_dien_thoai, mat_khau, vai_tro, ho_ten, anh_dai_dien, hoat_dong)
            VALUES (%s, %s, %s, %s, %s, NULL, %s)
        """
        values = (email, so_dien_thoai, mat_khau, "khach_hang", ho_ten, True)
        cursor.execute(sql, values)
        conn.commit()
        new_user_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Đăng ký thành công",
                "user": {
                    "id": new_user_id,
                    "email": email,
                    "name": ho_ten,
                    "createdAt": int(time.time() * 1000),
                    "avatarUrl": None,
                    "phoneNumber": so_dien_thoai
                }
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    
@app.get("/san-pham/{ma_san_pham}/tuy-chon")
def get_product_options(ma_san_pham: int):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT ltc.ma_loai_tuy_chon, ltc.ten_loai, ltc.loai_lua_chon, ltc.bat_buoc,
                   gttc.ma_gia_tri, gttc.ten_gia_tri, gttc.gia_them
            FROM TuyChonSanPham tsp
            JOIN LoaiTuyChon ltc ON tsp.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
            JOIN GiaTriTuyChon gttc ON gttc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
            WHERE tsp.ma_san_pham = %s AND gttc.hoat_dong = 1
            ORDER BY ltc.ma_loai_tuy_chon, gttc.thu_tu_hien_thi
        """

        cursor.execute(sql, (ma_san_pham,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        # Group theo loại tùy chọn
        from collections import defaultdict
        options_map = defaultdict(lambda: {"ma_loai_tuy_chon":None,"ten_loai": "", "loai_lua_chon": "", "bat_buoc": False, "gia_tri": []})

        for row in results:
            group = options_map[row["ma_loai_tuy_chon"]]
            group["ma_loai_tuy_chon"] = row["ma_loai_tuy_chon"]
            group["ten_loai"] = row["ten_loai"]
            group["loai_lua_chon"] = row["loai_lua_chon"]
            group["bat_buoc"] = bool(row["bat_buoc"])
            group["gia_tri"].append({
                "ma_gia_tri": row["ma_gia_tri"],
                "ten_gia_tri": row["ten_gia_tri"],
                "gia_them": row["gia_them"]
            })

        return {"tuy_chon": list(options_map.values())}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{ma_nguoi_dung}")
def get_user_by_id(ma_nguoi_dung: int):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM nguoidung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            return {"success": True, "user": user}
        else:
            return {"success": False, "message": "Không tìm thấy người dùng"}

    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-ngay-sinh")
def update_ngay_sinh(ma_nguoi_dung: int, ngay_sinh: str = Form(...)):
    try:
        # Validate date format (YYYY-MM-DD)
        from datetime import datetime
        try:
            # Kiểm tra format ngày sinh
            datetime.strptime(ngay_sinh, '%Y-%m-%d')
        except ValueError:
            return {
                "success": False,
                "message": "Định dạng ngày sinh không hợp lệ. Vui lòng sử dụng định dạng YYYY-MM-DD"
            }
        
        conn = db.connect_to_database()
        cursor = conn.cursor()
        
        # Kiểm tra người dùng có tồn tại không
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        user_exists = cursor.fetchone()
        
        if not user_exists:
            cursor.close()
            conn.close()
            return {
                "success": False,
                "message": "Người dùng không tồn tại"
            }
        
        # Cập nhật ngày sinh
        cursor.execute(
            "UPDATE NguoiDung SET ngay_sinh = %s WHERE ma_nguoi_dung = %s", 
            (ngay_sinh, ma_nguoi_dung)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": "Cập nhật ngày sinh thành công", 
            "ma_nguoi_dung": ma_nguoi_dung
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Lỗi server: {str(e)}"
        }

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-ten")
def update_ho_ten(ma_nguoi_dung: int, ho_ten: str = Form(...)):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE NguoiDung SET ho_ten = %s WHERE ma_nguoi_dung = %s",
            (ho_ten, ma_nguoi_dung)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Cập nhật họ tên thành công",
            "ma_nguoi_dung": ma_nguoi_dung
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Lỗi server: {str(e)}"
        }

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-mat-khau")
def doi_mat_khau(
    ma_nguoi_dung: int,
    mat_khau_cu: str = Form(...),
    mat_khau_moi: str = Form(...)
):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor()

        # Lấy mật khẩu cũ từ DB
        cursor.execute("SELECT mat_khau FROM NguoiDung WHERE ma_nguoi_dung = %s", (ma_nguoi_dung,))
        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "Người dùng không tồn tại"
            }

        mat_khau_trong_db = row[0]

        # So sánh mật khẩu cũ
        if mat_khau_cu != mat_khau_trong_db:
            return {
                "success": False,
                "message": "Mật khẩu cũ không đúng"
            }

        # Cập nhật mật khẩu mới
        cursor.execute(
            "UPDATE NguoiDung SET mat_khau = %s WHERE ma_nguoi_dung = %s",
            (mat_khau_moi, ma_nguoi_dung)
        )
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "success": True,
            "message": "Đổi mật khẩu thành công"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    
@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-email")
def update_email(ma_nguoi_dung: int, email: str = Form(...)):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor()
        cursor.execute("UPDATE NguoiDung SET email = %s WHERE ma_nguoi_dung = %s", (email, ma_nguoi_dung))
        conn.commit()
        cursor.close()
        conn.close()
        return {
            "success": True,  # ← Thêm field này
            "message": "Cập nhật email thành công", 
            "ma_nguoi_dung": ma_nguoi_dung
        }
    except Exception as e:
        return {
            "success": False,  # ← Thêm field này
            "message": f"Lỗi server: {str(e)}"
        }

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-so-dien-thoai")
def update_sdt(ma_nguoi_dung: int, so_dien_thoai: str = Form(...)):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor()
        cursor.execute("UPDATE NguoiDung SET so_dien_thoai = %s WHERE ma_nguoi_dung = %s", (so_dien_thoai, ma_nguoi_dung))
        conn.commit()
        cursor.close()
        conn.close()
        return {
            "success": True,  # ← Thêm field này
            "message": "Cập nhật số điện thoại thành công", 
            "ma_nguoi_dung": ma_nguoi_dung}
    except Exception as e:
        return {
            "success": False,  # ← Thêm field này
            "message": f"Lỗi server: {str(e)}"
        }

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-mat-khau")
def update_mat_khau(ma_nguoi_dung: int, mat_khau: str = Form(...)):
    try:
        conn = db.connect_to_database()
        cursor = conn.cursor()
        cursor.execute("UPDATE NguoiDung SET mat_khau = %s WHERE ma_nguoi_dung = %s", (mat_khau, ma_nguoi_dung))
        conn.commit()
        cursor.close()
        conn.close()
        return {"message": "Cập nhật mật khẩu thành công", "ma_nguoi_dung": ma_nguoi_dung}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.put("/nguoi-dung/{ma_nguoi_dung}/doi-anh-dai-dien")
def update_anh_dai_dien(ma_nguoi_dung: int, anh_dai_dien: UploadFile = File(...)):
    try:
        filename = f"user_{ma_nguoi_dung}_{anh_dai_dien.filename}"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(anh_dai_dien.file, buffer)

        image_path = f"/{save_path.replace(os.sep, '/')}"

        conn = db.connect_to_database()
        cursor = conn.cursor()
        cursor.execute("UPDATE NguoiDung SET anh_dai_dien = %s WHERE ma_nguoi_dung = %s", (image_path, ma_nguoi_dung))
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "message": "Cập nhật ảnh đại diện thành công",
            "ma_nguoi_dung": ma_nguoi_dung,
            "duong_dan": image_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật ảnh: {str(e)}")

@app.post("/dang-nhap")
def dang_nhap(
    tai_khoan: str = Form(...),  # có thể là email hoặc số điện thoại
    mat_khau: str = Form(...)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT * FROM NguoiDung
            WHERE (email = %s OR so_dien_thoai = %s) AND mat_khau = %s AND hoat_dong = TRUE
        """
        cursor.execute(sql, (tai_khoan, tai_khoan, mat_khau))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user:
            raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

        # Ẩn mật khẩu khi trả về
        user.pop("mat_khau", None)

        return {
            "message": "Đăng nhập thành công",
            "user": user
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/san-pham/{id}")
def get_san_pham_by_id(id: int):
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT ma_san_pham, ten_san_pham, hinh_anh, gia_co_ban, mo_ta, moi
                FROM SanPham
                WHERE ma_san_pham = %s
            """
            cursor.execute(sql, (id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                return result
            else:
                raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/hinh-anh-san-pham/{ma_san_pham}")
def get_hinh_anh_san_pham(ma_san_pham: int):
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT ma_hinh_anh, ma_san_pham, url_hinh_anh, thu_tu
                FROM HinhAnhSanPham
                WHERE ma_san_pham = %s
                ORDER BY thu_tu ASC
            """

            cursor.execute(sql, (ma_san_pham,))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            return results  # Trả về list cho Retrofit hoặc client dùng trực tiếp
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/getSanPhamHienThi")
def get_san_pham_hien_thi():
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT sp.ma_san_pham, sp.ten_san_pham, sp.gia_co_ban, sp.mo_ta,
                       sp.hinh_anh, sp.moi, dm.ten_danh_muc
                FROM SanPham sp
                LEFT JOIN DanhMuc dm ON sp.ma_danh_muc = dm.ma_danh_muc
                WHERE sp.hien_thi = 1
                ORDER BY sp.ngay_tao DESC
            """

            cursor.execute(sql)
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

            return rows

        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_FOLDER = "static/images/avatar"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PRODUCT_FOLDER = "static/images/product"
os.makedirs(PRODUCT_FOLDER, exist_ok=True)

@app.get("/danh-muc")
def get_all_danh_muc():
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT 
                    ma_danh_muc, 
                    ten_danh_muc, 
                    hinh_anh, 
                    mo_ta, 
                    thu_tu_hien_thi, 
                    hoat_dong
                FROM DanhMuc
                WHERE hoat_dong = 1
                ORDER BY thu_tu_hien_thi ASC
            """

            cursor.execute(sql)
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

            return rows

        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/san-pham/danh-muc/{ma_danh_muc}")
def get_san_pham_theo_danh_muc(ma_danh_muc: int):
    try:
        # Kết nối cơ sở dữ liệu
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # Kiểm tra danh mục có tồn tại
        cursor.execute("SELECT * FROM DanhMuc WHERE ma_danh_muc = %s AND hoat_dong = TRUE", (ma_danh_muc,))
        danh_muc = cursor.fetchone()
        if not danh_muc:
            raise HTTPException(status_code=404, detail="Không tìm thấy danh mục hoặc đã bị ẩn")

        # Lấy danh sách sản phẩm thuộc danh mục
        cursor.execute("""
            SELECT *
            FROM SanPham
            WHERE ma_danh_muc = %s AND hien_thi = TRUE
            ORDER BY ngay_cap_nhat DESC
        """, (ma_danh_muc,))
        ds_san_pham = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "ma_danh_muc": ma_danh_muc,
            "ten_danh_muc": danh_muc["ten_danh_muc"],
            "so_luong": len(ds_san_pham),
            "danh_sach_san_pham": ds_san_pham
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/addSanPham")
def add_san_pham(
    ten_san_pham: str = Form(...),
    gia_co_ban: float = Form(...),
    mo_ta: Optional[str] = Form(None),
    ma_danh_muc: Optional[int] = Form(None),
    loai_san_pham: Optional[str] = Form(None),
    hien_thi: bool = Form(True),
    moi: bool = Form(False),
    hinh_anh: UploadFile = File(None)
):
    try:
        # Xử lý lưu ảnh (nếu có)
        hinh_anh_path = None
        if hinh_anh:
            filename = f"{ten_san_pham.strip().replace(' ', '_')}_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

        # Kết nối và insert DB
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO SanPham (
                    ten_san_pham, hinh_anh, mo_ta, gia_co_ban, hien_thi,
                    ma_danh_muc, loai_san_pham, moi
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                ten_san_pham,
                hinh_anh_path,
                mo_ta,
                gia_co_ban,
                hien_thi,
                ma_danh_muc,
                loai_san_pham,
                moi
            )

            cursor.execute(sql, values)
            conn.commit()
            new_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return {
                "message": "Thêm sản phẩm thành công",
                "ma_san_pham": new_id,
                "hinh_anh": hinh_anh_path
            }
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    

    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            # Kiểm tra có tồn tại không
            cursor.execute("SELECT * FROM DanhMuc WHERE ma_danh_muc = %s", (ma_danh_muc,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")

            # Thực hiện xóa
            cursor.execute("DELETE FROM DanhMuc WHERE ma_danh_muc = %s", (ma_danh_muc,))
            conn.commit()

            cursor.close()
            conn.close()
            return {"message": "Xóa danh mục thành công"}
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.put("/san-pham/{id}")
def update_partial_san_pham(
    id: int = Path(...),
    ten_san_pham: Optional[str] = Form(None),
    gia_co_ban: Optional[float] = Form(None),
    mo_ta: Optional[str] = Form(None),
    ma_danh_muc: Optional[int] = Form(None),
    loai_san_pham: Optional[str] = Form(None),
    hien_thi: Optional[bool] = Form(None),
    moi: Optional[bool] = Form(None),
    hinh_anh: UploadFile = File(None)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        cursor = conn.cursor(dictionary=True)

        # ✅ Lấy dữ liệu hiện tại
        cursor.execute("SELECT * FROM SanPham WHERE ma_san_pham = %s", (id,))
        san_pham = cursor.fetchone()
        if not san_pham:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

        # ✅ Kiểm tra danh mục nếu gửi ma_danh_muc mới
        if ma_danh_muc is not None:
            cursor.execute("SELECT 1 FROM DanhMuc WHERE ma_danh_muc = %s", (ma_danh_muc,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")

        # ✅ Xử lý ảnh mới nếu có
        hinh_anh_path = None
        if hinh_anh:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{hinh_anh.filename.replace(' ', '_')}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

        # ✅ Gom các field cần cập nhật
        fields = []
        values = []

        if ten_san_pham is not None:
            fields.append("ten_san_pham = %s")
            values.append(ten_san_pham)
        if gia_co_ban is not None:
            fields.append("gia_co_ban = %s")
            values.append(gia_co_ban)
        if mo_ta is not None:
            fields.append("mo_ta = %s")
            values.append(mo_ta)
        if ma_danh_muc is not None:
            fields.append("ma_danh_muc = %s")
            values.append(ma_danh_muc)
        if loai_san_pham is not None:
            fields.append("loai_san_pham = %s")
            values.append(loai_san_pham)
        if hien_thi is not None:
            fields.append("hien_thi = %s")
            values.append(hien_thi)
        if moi is not None:
            fields.append("moi = %s")
            values.append(moi)
        if hinh_anh_path is not None:
            fields.append("hinh_anh = %s")
            values.append(hinh_anh_path)

        # ✅ Không có field nào để cập nhật
        if not fields:
            raise HTTPException(status_code=400, detail="Không có trường nào được cập nhật")

        # ✅ Thực hiện UPDATE
        sql = f"""
            UPDATE SanPham
            SET {', '.join(fields)}
            WHERE ma_san_pham = %s
        """
        values.append(id)

        cursor.execute(sql, tuple(values))
        conn.commit()

        cursor.close()
        conn.close()

        return {"message": "Cập nhật sản phẩm thành công", "ma_san_pham": id}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/addNguoiDung")
def add_nguoi_dung(
    ma_nguoi_dung: int,
    email: str = Form(...),
    so_dien_thoai: str = Form(None),
    mat_khau: str = Form(...),
    vai_tro: Literal['khach_hang', 'quan_tri_vien', 'bep', 'giao_hang', 'ho_tro', 'nhan_vien_cua_hang'] = Form(...),
    ho_ten: str = Form(None),
    anh_dai_dien: UploadFile = File(None),
    hoat_dong: bool = Form(True)
):
    try:
        # Xử lý lưu ảnh (nếu có)
        avatar_path = None
        if anh_dai_dien:
            filename = f"{email.replace('@', '_').replace('.', '_')}_{anh_dai_dien.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(anh_dai_dien.file, buffer)

            avatar_path = f"/{save_path.replace(os.sep, '/')}"  # Đường dẫn trả về (dùng làm URL nếu cần)

        # Kết nối và insert DB
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO NguoiDung (ma_nguoi_dung ,email, so_dien_thoai, mat_khau, vai_tro, ho_ten, anh_dai_dien, hoat_dong)
                VALUES (%s,%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                ma_nguoi_dung,
                email,
                so_dien_thoai,
                mat_khau,
                vai_tro,
                ho_ten,
                avatar_path,
                hoat_dong
            )

            cursor.execute(sql, values)
            conn.commit()
            new_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return {
                "message": "Thêm người dùng thành công",
                "ma_nguoi_dung": new_id,
                "anh_dai_dien": avatar_path
            }
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

CATEGORY_FOLDER = "static/images/category"
os.makedirs(CATEGORY_FOLDER, exist_ok=True)

@app.post("/addDanhMuc")
def add_danh_muc(
    ten_danh_muc: str = Form(...),
    hinh_anh: UploadFile = File(None),
    mo_ta: str = Form(None),
    thu_tu_hien_thi: int = Form(0),
    hoat_dong: bool = Form(True)
):
    try:
        # Xử lý upload ảnh
        hinh_anh_path = None
        if hinh_anh:
            filename = f"{ten_danh_muc.strip().replace(' ', '_')}_{hinh_anh.filename}"
            save_path = os.path.join(CATEGORY_FOLDER, filename)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"  # Chuẩn hóa dấu /

        # Kết nối và insert DB
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO DanhMuc (ten_danh_muc, hinh_anh, mo_ta, thu_tu_hien_thi, hoat_dong)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                ten_danh_muc,
                hinh_anh_path,
                mo_ta,
                thu_tu_hien_thi,
                hoat_dong
            )

            cursor.execute(sql, values)
            conn.commit()
            new_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return {
                "message": "Thêm danh mục thành công",
                "ma_danh_muc": new_id,
                "hinh_anh": hinh_anh_path
            }
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    


    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)
            sql = "SELECT * FROM DanhMuc"
            cursor.execute(sql)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            if results:
                return results
            else:
                return JSONResponse(status_code=204, content={"message": "Không có danh mục nào."})
        else:
            return JSONResponse(status_code=500, content={"message": "Lỗi kết nối cơ sở dữ liệu."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": f"Lỗi server: {str(e)}"})
    
@app.post("/themHinhAnhSanPham")
def add_hinh_anh_san_pham(
    ma_san_pham: int = Form(...),
    hinh_anh_list: List[UploadFile] = File(...),
    thu_tu_bat_dau: int = Form(0)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()
        added_images = []

        thu_tu = thu_tu_bat_dau
        for hinh_anh in hinh_anh_list:
            # Tạo đường dẫn lưu ảnh
            filename = f"{ma_san_pham}_{thu_tu}_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

            # Thêm vào DB
            sql = """
                INSERT INTO HinhAnhSanPham (ma_san_pham, url_hinh_anh, thu_tu) 
                VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (ma_san_pham, hinh_anh_path, thu_tu))
            conn.commit()

            added_images.append({
                "ma_san_pham": ma_san_pham,
                "url_hinh_anh": hinh_anh_path,
                "thu_tu": thu_tu
            })

            thu_tu += 1  # tăng thứ tự cho ảnh tiếp theo

        cursor.close()
        conn.close()

        return {
            "message": f"Đã thêm {len(added_images)} hình ảnh thành công.",
            "hinh_anh_san_pham": added_images
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")
    
@app.post("/themTuyChonCombo")
def add_tuy_chon_combo(
    ma_chi_tiet_combo: int,
    ma_loai_tuy_chon: int,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO TuyChonCombo (ma_chi_tiet_combo, ma_loai_tuy_chon) 
            VALUES (%s, %s)
        """
        adr = (ma_chi_tiet_combo, ma_loai_tuy_chon)
        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm tùy chọn combo thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm tùy chọn combo thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themDonHang")
def add_don_hang(
    ma_nguoi_dung: int,
    ma_cua_hang: int,
    tong_tien_san_pham: float,
    tong_tien_cuoi_cung: float,
    trang_thai: str,
    dia_chi_giao_hang: str,
    phuong_thuc_thanh_toan: str,
    trang_thai_thanh_toan: str,
    ma_giam_gia: int = None,
    ma_nhan_vien_cua_hang: int = None,
    ma_combo: int = None,
    ghi_chu: str = None,
    thoi_gian_giao_du_kien: str = None,
    phi_giao_hang: float = 0.00,
    giam_gia_ma_giam_gia: float = 0.00,
    giam_gia_combo: float = 0.00,
    so_dien_thoai_giao_hang: str = None,
):
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()
            sql = """
                INSERT INTO DonHang (ma_nguoi_dung, ma_cua_hang, tong_tien_san_pham, 
             phi_giao_hang, giam_gia_ma_giam_gia, 
                                     giam_gia_combo, tong_tien_cuoi_cung, 
                                     trang_thai, dia_chi_giao_hang, 
                                     so_dien_thoai_giao_hang, phuong_thuc_thanh_toan, 
                                     trang_thai_thanh_toan, ma_giam_gia, 
                                     ma_nhan_vien_cua_hang, ma_combo, 
                                     ghi_chu, thoi_gian_giao_du_kien) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            adr = (
                ma_nguoi_dung,
                ma_cua_hang,
                tong_tien_san_pham,
                phi_giao_hang,
                giam_gia_ma_giam_gia,
                giam_gia_combo,
                tong_tien_cuoi_cung,
                trang_thai,
                dia_chi_giao_hang,
                so_dien_thoai_giao_hang,
                phuong_thuc_thanh_toan,
                trang_thai_thanh_toan,
                ma_giam_gia,
                ma_nhan_vien_cua_hang,
                ma_combo,
                ghi_chu,
                thoi_gian_giao_du_kien,
            )

            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm đơn hàng thành công."}
        else:
            print(f"Lỗi kết nối: {conn}")
            return {"message": "Lỗi kết nối cơ sở dữ liệu."}
    except Exception as e:
        print(f"Lỗi server: {str(e)}")  # Ghi log lỗi
        if conn:
            conn.close()
        return {"message": "Thêm đơn hàng thất bại: " + str(e)}

@app.post("/themChiTietComboDonHang")
def add_chi_tiet_combo_don_hang(
    ma_mat_hang_don_hang: int,
    ma_san_pham: int,
    ten_san_pham: str,
    so_luong: int,
    don_gia: float,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChiTietComboDonHang (ma_mat_hang_don_hang, ma_san_pham, 
                                              ten_san_pham, so_luong, don_gia) 
            VALUES (%s, %s, %s, %s, %s)
        """
        adr = (
            ma_mat_hang_don_hang,
            ma_san_pham,
            ten_san_pham,
            so_luong,
            don_gia,
        )

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chi tiết combo vào đơn hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chi tiết combo vào đơn hàng thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themChiTietTuyChonDonHang")
def add_chi_tiet_tuy_chon_don_hang(
    ma_mat_hang_don_hang: int,
    ma_gia_tri: int,
    ten_loai_tuy_chon: str,
    ten_gia_tri: str,
    gia_them: float,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChiTietTuyChonDonHang (ma_mat_hang_don_hang, ma_gia_tri, 
                                                ten_loai_tuy_chon, ten_gia_tri, gia_them) 
            VALUES (%s, %s, %s, %s, %s)
        """
        adr = (
            ma_mat_hang_don_hang,
            ma_gia_tri,
            ten_loai_tuy_chon,
            ten_gia_tri,
            gia_them,
        )

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chi tiết tùy chọn vào đơn hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chi tiết tùy chọn vào đơn hàng thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themPhanCongDonHang")
def add_phan_cong_don_hang(
    ma_don_hang: int,
    ma_nguoi_giao_hang: int,
    trang_thai: str = 'da_phan_cong',  # Giá trị mặc định
):
    if trang_thai not in ['da_phan_cong', 'da_chap_nhan', 'da_tu_choi', 'hoan_thanh']:
        return {"message": "Trạng thái không hợp lệ."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO PhanCongDonHang (ma_don_hang, ma_nguoi_giao_hang, trang_thai) 
            VALUES (%s, %s, %s)
        """
        adr = (ma_don_hang, ma_nguoi_giao_hang, trang_thai)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm phân công đơn hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm phân công đơn hàng thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themChuyenDonHang")
def add_chuyen_don_hang(
    ma_don_hang: int,
    ma_nguoi_chuyen: int,
    ma_nguoi_nhan: int,
    loai_chuyen: str,
):
    if loai_chuyen not in ['toi_bep', 'toi_giao_hang']:
        return {"message": "Loại chuyển không hợp lệ."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChuyenDonHang (ma_don_hang, ma_nguoi_chuyen, ma_nguoi_nhan, loai_chuyen) 
            VALUES (%s, %s, %s, %s)
        """
        adr = (ma_don_hang, ma_nguoi_chuyen, ma_nguoi_nhan, loai_chuyen)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chuyển đơn hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chuyển đơn hàng thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}
    
@app.post("/themDanhGia")
def add_danh_gia(
    ma_nguoi_dung: int,
    ma_san_pham: int,
    ma_don_hang: int,
    diem_so: int,
    binh_luan: str = None,
    hinh_anh_danh_gia: str = None,  # Có thể là JSON array chứa các URL hình ảnh
):
    if diem_so < 1 or diem_so > 5:
        return {"message": "Điểm số phải nằm trong khoảng từ 1 đến 5."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO DanhGia (ma_nguoi_dung, ma_san_pham, ma_don_hang, diem_so, binh_luan, hinh_anh_danh_gia) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        adr = (ma_nguoi_dung, ma_san_pham, ma_don_hang, diem_so, binh_luan, hinh_anh_danh_gia)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm đánh giá thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm đánh giá thất bại: " + str(e)}
    else:
        print(f"Lỗi kết nối: {conn}")
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themSanPhamYeuThich")
def add_san_pham_yeu_thich(
    ma_nguoi_dung: int,
    ma_san_pham: int,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()

        # Kiểm tra xem sản phẩm đã được yêu thích chưa để tránh trùng lặp
        check_sql = "SELECT ma_yeu_thich FROM SanPhamYeuThich WHERE ma_nguoi_dung = %s AND ma_san_pham = %s"
        cursor.execute(check_sql, (ma_nguoi_dung, ma_san_pham))
        exists = cursor.fetchone()
        if exists:
            cursor.close()
            conn.close()
            return {"message": "Sản phẩm đã được người dùng yêu thích trước đó."}

        insert_sql = "INSERT INTO SanPhamYeuThich (ma_nguoi_dung, ma_san_pham) VALUES (%s, %s)"
        try:
            cursor.execute(insert_sql, (ma_nguoi_dung, ma_san_pham))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm sản phẩm yêu thích thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm sản phẩm yêu thích thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.get("/san-pham-yeu-thich")
def get_san_pham_yeu_thich(ma_nguoi_dung: int):
    conn = db.connect_to_database()
    if isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT sp.*
            FROM SanPhamYeuThich syt
            JOIN SanPham sp ON syt.ma_san_pham = sp.ma_san_pham
            WHERE syt.ma_nguoi_dung = %s
        """
        cursor.execute(sql, (ma_nguoi_dung,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/xoaSanPhamYeuThich")
def remove_san_pham_yeu_thich(
    ma_nguoi_dung: int,
    ma_san_pham: int,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()

        # Kiểm tra xem sản phẩm có tồn tại trong danh sách yêu thích không
        check_sql = "SELECT ma_yeu_thich FROM SanPhamYeuThich WHERE ma_nguoi_dung = %s AND ma_san_pham = %s"
        cursor.execute(check_sql, (ma_nguoi_dung, ma_san_pham))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.close()
            conn.close()
            return {"message": "Sản phẩm không có trong danh sách yêu thích."}

        delete_sql = "DELETE FROM SanPhamYeuThich WHERE ma_nguoi_dung = %s AND ma_san_pham = %s"
        try:
            cursor.execute(delete_sql, (ma_nguoi_dung, ma_san_pham))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Xóa sản phẩm yêu thích thành công."}
        except Error as e:
            conn.close()
            return {"message": "Xóa sản phẩm yêu thích thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.get("/kiemTraYeuThich")
def check_is_favorite(
    ma_nguoi_dung: int,
    ma_san_pham: int
):
    conn = db.connect_to_database()
    if isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    
    try:
        cursor = conn.cursor()
        sql = "SELECT COUNT(*) as count FROM SanPhamYeuThich WHERE ma_nguoi_dung = %s AND ma_san_pham = %s"
        cursor.execute(sql, (ma_nguoi_dung, ma_san_pham))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        is_favorite = result[0] > 0 if result else False
        return {"isFavorite": is_favorite}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/san-pham-yeu-thich-chi-tiet")
def get_san_pham_yeu_thich_with_details(ma_nguoi_dung: int):
    conn = db.connect_to_database()
    if isinstance(conn, Error):
        raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT 
                syt.ma_yeu_thich,
                syt.ma_nguoi_dung,
                sp.ma_san_pham,
                sp.ten_san_pham,
                sp.gia_co_ban,
                sp.mo_ta,
                sp.hinh_anh AS url_hinh_anh,
                sp.hien_thi,
                sp.ma_danh_muc,
                dm.ten_danh_muc
            FROM SanPhamYeuThich syt
            JOIN SanPham sp ON syt.ma_san_pham = sp.ma_san_pham
            LEFT JOIN DanhMuc dm ON sp.ma_danh_muc = dm.ma_danh_muc
            WHERE syt.ma_nguoi_dung = %s AND sp.hien_thi = 1
            ORDER BY syt.ma_yeu_thich DESC
        """
        cursor.execute(sql, (ma_nguoi_dung,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"data": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/themMaGiamGiaNguoiDung")
def add_ma_giam_gia_nguoi_dung(
    ma_nguoi_dung: int,
    ma_giam_gia: int,
    so_lan_su_dung: int = 0,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()

        # Kiểm tra xem đã tồn tại bản ghi cho người dùng và mã giảm giá này chưa
        check_sql = """
            SELECT ma_giam_gia_nguoi_dung FROM MaGiamGiaNguoiDung 
            WHERE ma_nguoi_dung = %s AND ma_giam_gia = %s
        """
        cursor.execute(check_sql, (ma_nguoi_dung, ma_giam_gia))
        exists = cursor.fetchone()
        if exists:
            cursor.close()
            conn.close()
            return {"message": "Mã giảm giá của người dùng đã tồn tại."}

        insert_sql = """
            INSERT INTO MaGiamGiaNguoiDung (ma_nguoi_dung, ma_giam_gia, so_lan_su_dung) 
            VALUES (%s, %s, %s)
        """
        try:
            cursor.execute(insert_sql, (ma_nguoi_dung, ma_giam_gia, so_lan_su_dung))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm mã giảm giá cho người dùng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm mã giảm giá cho người dùng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themDiemThuong")
def add_diem_thuong(
    ma_nguoi_dung: int,
    diem: int = 0,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()

        # Kiểm tra nếu đã có bản ghi điểm thưởng cho người dùng này chưa
        check_sql = "SELECT ma_diem_thuong FROM DiemThuong WHERE ma_nguoi_dung = %s"
        cursor.execute(check_sql, (ma_nguoi_dung,))
        exists = cursor.fetchone()

        if exists:
            cursor.close()
            conn.close()
            return {"message": "Người dùng đã có điểm thưởng. Vui lòng sử dụng cập nhật."}

        insert_sql = "INSERT INTO DiemThuong (ma_nguoi_dung, diem) VALUES (%s, %s)"
        try:
            cursor.execute(insert_sql, (ma_nguoi_dung, diem))
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm điểm thưởng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm điểm thưởng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themTroChuyen")
def add_tro_chuyen(
    ma_nguoi_dung: int,
    ma_nhan_vien_ho_tro: int,
    noi_dung: str,
    nguoi_gui: str,
):
    if nguoi_gui not in ['khach_hang', 'nhan_vien']:
        return {"message": "Giá trị 'nguoi_gui' phải là 'khach_hang' hoặc 'nhan_vien'."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO TroChuyen (ma_nguoi_dung, ma_nhan_vien_ho_tro, noi_dung, nguoi_gui) 
            VALUES (%s, %s, %s, %s)
        """
        adr = (ma_nguoi_dung, ma_nhan_vien_ho_tro, noi_dung, nguoi_gui)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm trò chuyện thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm trò chuyện thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themLichLamViec")
def add_lich_lam_viec(
    ma_nguoi_dung: int,
    thoi_gian_bat_dau: str,
    thoi_gian_ket_thuc: str,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO LichLamViec (ma_nguoi_dung, thoi_gian_bat_dau, thoi_gian_ket_thuc) 
            VALUES (%s, %s, %s)
        """
        adr = (ma_nguoi_dung, thoi_gian_bat_dau, thoi_gian_ket_thuc)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm lịch làm việc thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm lịch làm việc thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.get("/danhSachBanner")
def get_all_banners():
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                ma_banner,
                url_hinh_anh,
                ma_san_pham,
                tieu_de,
                thu_tu_hien_thi,
                hoat_dong,
                ngay_tao
            FROM Banner
            ORDER BY thu_tu_hien_thi ASC, ngay_tao DESC
        """)
        banners = cursor.fetchall()

        cursor.close()
        conn.close()

        return banners  # Trả về danh sách banner dạng List<Dict>

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.delete("/xoaBanner/{ma_banner}")
def delete_banner(ma_banner: int):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Kiểm tra xem banner tồn tại không
        cursor.execute("SELECT url_hinh_anh FROM Banner WHERE ma_banner = %s", (ma_banner,))
        banner = cursor.fetchone()

        if not banner:
            raise HTTPException(status_code=404, detail="Không tìm thấy banner")

        # Xoá file ảnh khỏi hệ thống (nếu tồn tại)
        if banner[0]:  # url_hinh_anh
            image_path = banner[0].lstrip("/")
            if os.path.exists(image_path):
                os.remove(image_path)

        # Xoá banner khỏi DB
        cursor.execute("DELETE FROM Banner WHERE ma_banner = %s", (ma_banner,))
        conn.commit()

        cursor.close()
        conn.close()

        return {"message": f"Xoá banner {ma_banner} thành công."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/banner-hoat-dong")
def get_active_banners():
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT ma_banner, url_hinh_anh, ma_san_pham, tieu_de, thu_tu_hien_thi, hoat_dong
                FROM Banner
                WHERE hoat_dong = 1
                ORDER BY thu_tu_hien_thi ASC
            """
            cursor.execute(sql)
            banners = cursor.fetchall()

            cursor.close()
            conn.close()

            return banners  # Retrofit expect List<Banner>

        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.put("/capNhatBanner/{ma_banner}")
def update_banner(
    ma_banner: int,
    ma_san_pham: Optional[int] = Form(None),
    tieu_de: Optional[str] = Form(None),
    thu_tu_hien_thi: Optional[int] = Form(None),
    hoat_dong: Optional[bool] = Form(None),
    hinh_anh: Optional[UploadFile] = File(None)
):
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
        
        cursor = conn.cursor(dictionary=True)

        # Lấy dữ liệu cũ
        cursor.execute("SELECT * FROM Banner WHERE ma_banner = %s", (ma_banner,))
        banner = cursor.fetchone()

        if not banner:
            raise HTTPException(status_code=404, detail="Không tìm thấy banner")

        # Cập nhật ảnh nếu có
        hinh_anh_path = banner["url_hinh_anh"]
        if hinh_anh:
            filename = f"banner_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)
            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

        # Dùng dữ liệu cũ nếu không truyền mới
        sql = """
            UPDATE Banner SET
                url_hinh_anh = %s,
                ma_san_pham = %s,
                tieu_de = %s,
                thu_tu_hien_thi = %s,
                hoat_dong = %s
            WHERE ma_banner = %s
        """
        values = (
            hinh_anh_path,
            ma_san_pham if ma_san_pham is not None else banner["ma_san_pham"],
            tieu_de if tieu_de is not None else banner["tieu_de"],
            thu_tu_hien_thi if thu_tu_hien_thi is not None else banner["thu_tu_hien_thi"],
            hoat_dong if hoat_dong is not None else banner["hoat_dong"],
            ma_banner
        )

        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Cập nhật banner thành công."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/themBanner")
def add_banner(
    ma_san_pham: int = Form(None),
    tieu_de: str = Form(None),
    thu_tu_hien_thi: int = Form(0),
    hoat_dong: bool = Form(True),
    hinh_anh: UploadFile = File(...)
):
    try:
        # Xử lý lưu ảnh
        hinh_anh_path = None
        if hinh_anh:
            filename = f"banner_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"  # đường dẫn lưu

        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO Banner (url_hinh_anh, ma_san_pham, tieu_de, thu_tu_hien_thi, hoat_dong)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                hinh_anh_path,
                ma_san_pham,
                tieu_de,
                thu_tu_hien_thi,
                hoat_dong
            )

            cursor.execute(sql, values)
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "message": "Thêm banner thành công.",
                "hinh_anh": hinh_anh_path
            }

        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.post("/themOTP")
def add_otp(
    ma_nguoi_dung: int,
    otp_code: str,
    loai_otp: str,
    het_han: str,
):
    if loai_otp not in ['reset_password', 'verify_email', 'verify_phone']:
        return {"message": "Loại OTP không hợp lệ."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO OTP (ma_nguoi_dung, otp_code, loai_otp, het_han) 
            VALUES (%s, %s, %s, %s)
        """
        adr = (ma_nguoi_dung, otp_code, loai_otp, het_han)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm OTP thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm OTP thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themThongTinCuaHang")
def add_thong_tin_cua_hang(
    ten_cua_hang: str,
    dia_chi: str,
    so_dien_thoai: str = None,
    email: str = None,
    gio_mo: str = None,
    gio_dong: str = None,
    hoat_dong: bool = True,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ThongTinCuaHang (ten_cua_hang, dia_chi, so_dien_thoai, email, gio_mo, gio_dong, hoat_dong) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        adr = (ten_cua_hang, dia_chi, so_dien_thoai, email, gio_mo, gio_dong, hoat_dong)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm thông tin cửa hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm thông tin cửa hàng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themChiTietTuyChonGioHang")
def add_chi_tiet_tuy_chon_gio_hang(
    ma_mat_hang_gio_hang: int,
    ma_gia_tri: int,
    gia_them: float,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChiTietTuyChonGioHang (ma_mat_hang_gio_hang, ma_gia_tri, gia_them) 
            VALUES (%s, %s, %s)
        """
        adr = (ma_mat_hang_gio_hang, ma_gia_tri, gia_them)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chi tiết tùy chọn giỏ hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chi tiết tùy chọn giỏ hàng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themMatHangGioHang")
def add_mat_hang_gio_hang(
    ma_gio_hang: int,
        loai_mat_hang: str,
    so_luong: int,
    gia_san_pham: float,
    ma_san_pham: int = None,
    ma_combo: int = None,
    ghi_chu: str = None,
):
    if loai_mat_hang not in ['san_pham', 'combo']:
        return {"message": "Loại mặt hàng không hợp lệ."}

    if (ma_san_pham is None and ma_combo is None) or (ma_san_pham is not None and ma_combo is not None):
        return {"message": "Phải cung cấp mã sản phẩm hoặc mã combo, nhưng không cả hai."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO MatHangGioHang (ma_gio_hang, ma_san_pham, ma_combo, loai_mat_hang, so_luong, gia_san_pham, ghi_chu) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        adr = (ma_gio_hang, ma_san_pham, ma_combo, loai_mat_hang, so_luong, gia_san_pham, ghi_chu)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm mặt hàng vào giỏ hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm mặt hàng vào giỏ hàng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/taoGioHang")
def tao_gio_hang(ma_nguoi_dung: int):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()

        # Kiểm tra nếu người dùng đã có giỏ hàng chưa
        check_sql = "SELECT ma_gio_hang FROM GioHang WHERE ma_nguoi_dung = %s"
        cursor.execute(check_sql, (ma_nguoi_dung,))
        exists = cursor.fetchone()
        if exists:
            cursor.close()
            conn.close()
            return {"message": "Người dùng đã có giỏ hàng."}

        insert_sql = "INSERT INTO GioHang (ma_nguoi_dung) VALUES (%s)"
        try:
            cursor.execute(insert_sql, (ma_nguoi_dung,))
            conn.commit()
            ma_gio_hang = cursor.lastrowid
            cursor.close()
            conn.close()
            return {"message": "Tạo giỏ hàng thành công.", "ma_gio_hang": ma_gio_hang}
        except Error as e:
            conn.close()
            return {"message": "Tạo giỏ hàng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themGiaTriTuyChon")
def add_gia_tri_tuy_chon(
    ma_loai_tuy_chon: int,
    ten_gia_tri: str,
    gia_them: float = 0.00,
    mo_ta: str = None,
    thu_tu_hien_thi: int = 0,
    hoat_dong: bool = True,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO GiaTriTuyChon (ma_loai_tuy_chon, ten_gia_tri, gia_them, mo_ta, thu_tu_hien_thi, hoat_dong) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        adr = (ma_loai_tuy_chon, ten_gia_tri, gia_them, mo_ta, thu_tu_hien_thi, hoat_dong)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm giá trị tùy chọn thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm giá trị tùy chọn thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themTuyChonSanPham")
def add_tuy_chon_san_pham(
    ma_san_pham: int,
    ma_loai_tuy_chon: int,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO TuyChonSanPham (ma_san_pham, ma_loai_tuy_chon) 
            VALUES (%s, %s)
        """
        adr = (ma_san_pham, ma_loai_tuy_chon)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm tùy chọn sản phẩm thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm tùy chọn sản phẩm thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themLoaiTuyChon")
def add_loai_tuy_chon(
    ten_loai: str,
    mo_ta: str = None,
    loai_lua_chon: str = 'single',
    bat_buoc: bool = False,
):
    if loai_lua_chon not in ['single', 'multiple']:
        return {"message": "Giá trị 'loai_lua_chon' phải là 'single' hoặc 'multiple'."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO LoaiTuyChon (ten_loai, mo_ta, loai_lua_chon, bat_buoc) 
            VALUES (%s, %s, %s, %s)
        """
        adr = (ten_loai, mo_ta, loai_lua_chon, bat_buoc)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm loại tùy chọn thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm loại tùy chọn thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}
    
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(       # cái này  của web đừng xóa nha
    CORSMiddleware,
    allow_origins=["*"],  # hoặc ["http://127.0.0.1:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  
)
