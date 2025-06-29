from fastapi import File, UploadFile, FastAPI, HTTPException, Form, Path, Query
import os, shutil
from typing import Literal, Optional, List, Annotated
from mysql.connector import Error
import db
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import date, datetime
import time
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
import string
import random
import asyncio
import logging


app = FastAPI()

UPLOAD_FOLDER = "uploads"



# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class ThongTinGiaoHangCreate(BaseModel):
    ten_nguoi_nhan: str
    so_dien_thoai_nguoi_nhan: str
    so_duong: str
    phuong_xa: Optional[str] = None
    quan_huyen: Optional[str] = None
    tinh_thanh_pho: Optional[str] = None
    la_dia_chi_mac_dinh: bool = False
    ghi_chu: Optional[str] = None

class ThongTinGiaoHangUpdate(BaseModel):
    ten_nguoi_nhan: Optional[str] = None
    so_dien_thoai_nguoi_nhan: Optional[str] = None
    so_duong: Optional[str] = None
    phuong_xa: Optional[str] = None
    quan_huyen: Optional[str] = None
    tinh_thanh_pho: Optional[str] = None
    la_dia_chi_mac_dinh: Optional[bool] = None
    ghi_chu: Optional[str] = None

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
        
        # Thêm địa chỉ mới
        insert_query = """
        INSERT INTO ThongTinGiaoHang 
        (ma_nguoi_dung, ten_nguoi_nhan, so_dien_thoai_nguoi_nhan, so_duong, 
         phuong_xa, quan_huyen, tinh_thanh_pho, la_dia_chi_mac_dinh, ghi_chu)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            address_data.ghi_chu
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
def get_delivery_addresses(ma_nguoi_dung: int):
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
        
        # Lấy danh sách địa chỉ
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
    Xóa địa chỉ giao hàng
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
        
        # Kiểm tra xem địa chỉ này có đang được sử dụng trong đơn hàng nào không
        cursor.execute("""
            SELECT COUNT(*) as count FROM DonHang 
            WHERE ma_nguoi_dung = %s AND dia_chi_giao_hang LIKE %s
        """, (ma_nguoi_dung, f"%{address['so_duong']}%"))
        
        result = cursor.fetchone()
        if result['count'] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa địa chỉ đang được sử dụng trong đơn hàng"
            )
        
        # Xóa địa chỉ
        cursor.execute("""
            DELETE FROM ThongTinGiaoHang 
            WHERE ma_thong_tin_giao_hang = %s AND ma_nguoi_dung = %s
        """, (ma_thong_tin_giao_hang, ma_nguoi_dung))
        
        conn.commit()
        
        # Nếu xóa địa chỉ mặc định, đặt địa chỉ khác làm mặc định (nếu có)
        if address['la_dia_chi_mac_dinh']:
            cursor.execute("""
                SELECT ma_thong_tin_giao_hang FROM ThongTinGiaoHang 
                WHERE ma_nguoi_dung = %s 
                ORDER BY ngay_cap_nhat DESC 
                LIMIT 1
            """, (ma_nguoi_dung,))
            
            next_default = cursor.fetchone()
            if next_default:
                cursor.execute("""
                    UPDATE ThongTinGiaoHang 
                    SET la_dia_chi_mac_dinh = TRUE 
                    WHERE ma_thong_tin_giao_hang = %s
                """, (next_default['ma_thong_tin_giao_hang'],))
                conn.commit()
        
        return {
            "success": True,
            "message": "Xóa địa chỉ giao hàng thành công",
            "data": {
                "ma_thong_tin_giao_hang": ma_thong_tin_giao_hang,
                "ma_nguoi_dung": ma_nguoi_dung
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
    Đặt địa chỉ giao hàng làm mặc định
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

async def send_email(to_email: str, password: str):
    message = MessageSchema(
        subject="Mật khẩu mới từ Pizza App",
        recipients=[to_email],
        body=f"""
            <p>Chào bạn,</p>
            <p>Mật khẩu mới của bạn là: <strong>{password}</strong></p>
            <p>Vui lòng đăng nhập và đổi lại mật khẩu nếu cần.</p>
            <p>-- Pizza App Team --</p>
        """,
        subtype="html"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

@app.post("/quen-mat-khau")
async def quen_mat_khau(email: EmailStr = Form(...)):
    conn = db.connect_to_database()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM NguoiDung WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại")

    new_password = generate_password()

    cursor.execute("UPDATE NguoiDung SET mat_khau = %s WHERE email = %s", (new_password, email))
    conn.commit()

    await send_email(email, new_password)

    return {"message": "Mật khẩu mới đã được gửi về email của bạn"}

class DatHangRequest(BaseModel):
    ma_nguoi_dung: int
    ma_cua_hang: Optional[int] = None
    dia_chi_giao_hang: str
    so_dien_thoai_giao_hang: str
    phuong_thuc_thanh_toan: str  # 'tien_mat', 'chuyen_khoan', 'the_tin_dung', 'vi_dien_tu'
    ma_giam_gia: Optional[int] = None
    ghi_chu: Optional[str] = None
    thoi_gian_giao_du_kien: Optional[str] = None  # Format: 'YYYY-MM-DD HH:MM:SS'

@app.post("/datHang")
def dat_hang(request: DatHangRequest):
    """Đặt hàng từ giỏ hàng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # 1. Kiểm tra người dùng tồn tại
        cursor.execute("SELECT ma_nguoi_dung FROM NguoiDung WHERE ma_nguoi_dung = %s", 
                      (request.ma_nguoi_dung,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Người dùng không tồn tại")

        # 2. Lấy giỏ hàng
        cursor.execute("SELECT ma_gio_hang FROM GioHang WHERE ma_nguoi_dung = %s", 
                      (request.ma_nguoi_dung,))
        gio_hang = cursor.fetchone()
        
        if not gio_hang:
            raise HTTPException(status_code=404, detail="Giỏ hàng trống")

        ma_gio_hang = gio_hang['ma_gio_hang']

        # 3. Lấy các mặt hàng trong giỏ
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
                c.ten_combo
            FROM MatHangGioHang mhgh
            LEFT JOIN SanPham sp ON mhgh.ma_san_pham = sp.ma_san_pham
            LEFT JOIN Combo c ON mhgh.ma_combo = c.ma_combo
            WHERE mhgh.ma_gio_hang = %s
        """, (ma_gio_hang,))
        
        mat_hang_list = cursor.fetchall()
        
        if not mat_hang_list:
            raise HTTPException(status_code=400, detail="Giỏ hàng trống")

        # 4. Tính toán giá tiền
        tong_tien_san_pham = 0
        chi_tiet_don_hang = []

        for mat_hang in mat_hang_list:
            tong_gia_tuy_chon = 0
            
            # Tính giá tùy chọn cho sản phẩm đơn lẻ
            if mat_hang['loai_mat_hang'] == 'san_pham':
                cursor.execute("""
                    SELECT gia_them FROM ChiTietTuyChonGioHang 
                    WHERE ma_mat_hang_gio_hang = %s
                """, (mat_hang['ma_mat_hang_gio_hang'],))
                
                tuy_chon_list = cursor.fetchall()
                tong_gia_tuy_chon = sum(tc['gia_them'] for tc in tuy_chon_list)
            
            # Tính giá tùy chọn cho combo
            elif mat_hang['loai_mat_hang'] == 'combo':
                cursor.execute("""
                    SELECT SUM(tccgh.gia_them) as tong_gia_tuy_chon
                    FROM TuyChonComboGioHang tccgh
                    JOIN ChiTietComboGioHang ctcgh ON tccgh.ma_chi_tiet_combo_gio_hang = ctcgh.ma_chi_tiet
                    WHERE ctcgh.ma_mat_hang_gio_hang = %s
                """, (mat_hang['ma_mat_hang_gio_hang'],))
                
                result = cursor.fetchone()
                tong_gia_tuy_chon = result['tong_gia_tuy_chon'] or 0

            thanh_tien = (mat_hang['gia_san_pham'] + tong_gia_tuy_chon) * mat_hang['so_luong']
            tong_tien_san_pham += thanh_tien
            
            chi_tiet_don_hang.append({
                'mat_hang': mat_hang,
                'tong_gia_tuy_chon': tong_gia_tuy_chon,
                'thanh_tien': thanh_tien
            })

        # 5. Xử lý mã giảm giá
        giam_gia_ma_giam_gia = 0
        if request.ma_giam_gia:
            cursor.execute("""
                SELECT 
                    loai_giam_gia,
                    gia_tri_giam,
                    gia_tri_don_hang_toi_thieu,
                    so_lan_su_dung_toi_da,
                    da_su_dung,
                    ngay_bat_dau,
                    ngay_ket_thuc,
                    hoat_dong
                FROM MaGiamGia 
                WHERE ma_giam_gia = %s
            """, (request.ma_giam_gia,))
            
            ma_giam_gia_info = cursor.fetchone()
            
            if not ma_giam_gia_info:
                raise HTTPException(status_code=404, detail="Mã giảm giá không tồn tại")
            
            if not ma_giam_gia_info['hoat_dong']:
                raise HTTPException(status_code=400, detail="Mã giảm giá đã hết hiệu lực")
            
            # Kiểm tra điều kiện áp dụng
            if ma_giam_gia_info['gia_tri_don_hang_toi_thieu'] and tong_tien_san_pham < ma_giam_gia_info['gia_tri_don_hang_toi_thieu']:
                raise HTTPException(status_code=400, detail=f"Đơn hàng tối thiểu {ma_giam_gia_info['gia_tri_don_hang_toi_thieu']} để áp dụng mã giảm giá")
            
            if ma_giam_gia_info['so_lan_su_dung_toi_da'] and ma_giam_gia_info['da_su_dung'] >= ma_giam_gia_info['so_lan_su_dung_toi_da']:
                raise HTTPException(status_code=400, detail="Mã giảm giá đã hết lượt sử dụng")
            
            # Tính giảm giá
            if ma_giam_gia_info['loai_giam_gia'] == 'phan_tram':
                giam_gia_ma_giam_gia = tong_tien_san_pham * ma_giam_gia_info['gia_tri_giam'] / 100
            else:  # 'co_dinh'
                giam_gia_ma_giam_gia = ma_giam_gia_info['gia_tri_giam']
            
            # Giảm giá không được vượt quá tổng tiền sản phẩm
            giam_gia_ma_giam_gia = min(giam_gia_ma_giam_gia, tong_tien_san_pham)

        # 6. Tính phí giao hàng (có thể customize logic này)
        phi_giao_hang = 30000  # Phí cố định 30k, có thể tính theo khoảng cách
        
        # 7. Tính tổng tiền cuối cùng
        tong_tien_cuoi_cung = tong_tien_san_pham + phi_giao_hang - giam_gia_ma_giam_gia
        
        # 8. Tạo đơn hàng
        cursor.execute("""
            INSERT INTO DonHang (
                ma_nguoi_dung, ma_cua_hang, tong_tien_san_pham, phi_giao_hang,
                giam_gia_ma_giam_gia, giam_gia_combo, tong_tien_cuoi_cung,
                trang_thai, dia_chi_giao_hang, so_dien_thoai_giao_hang,
                phuong_thuc_thanh_toan, trang_thai_thanh_toan, ma_giam_gia,
                ghi_chu, thoi_gian_giao_du_kien
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            request.ma_nguoi_dung, request.ma_cua_hang, tong_tien_san_pham, phi_giao_hang,
            giam_gia_ma_giam_gia, 0, tong_tien_cuoi_cung,
            'da_nhan', request.dia_chi_giao_hang, request.so_dien_thoai_giao_hang,
            request.phuong_thuc_thanh_toan, 'cho_xu_ly', request.ma_giam_gia,
            request.ghi_chu, request.thoi_gian_giao_du_kien
        ))
        
        ma_don_hang = cursor.lastrowid

        # 9. Chuyển các mặt hàng từ giỏ hàng sang đơn hàng
        for chi_tiet in chi_tiet_don_hang:
            mat_hang = chi_tiet['mat_hang']
            
            cursor.execute("""
                INSERT INTO MatHangDonHang (
                    ma_don_hang, ma_san_pham, ma_combo, loai_mat_hang,
                    so_luong, don_gia_co_ban, tong_gia_tuy_chon, thanh_tien, ghi_chu
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ma_don_hang, mat_hang['ma_san_pham'], mat_hang['ma_combo'],
                mat_hang['loai_mat_hang'], mat_hang['so_luong'], mat_hang['gia_san_pham'],
                chi_tiet['tong_gia_tuy_chon'], chi_tiet['thanh_tien'], mat_hang['ghi_chu']
            ))
            
            ma_mat_hang_don_hang = cursor.lastrowid

            # 10. Chuyển tùy chọn từ giỏ hàng sang đơn hàng
            if mat_hang['loai_mat_hang'] == 'san_pham':
                # Tùy chọn sản phẩm đơn lẻ
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
                
                tuy_chon_list = cursor.fetchall()
                
                for tuy_chon in tuy_chon_list:
                    cursor.execute("""
                        INSERT INTO ChiTietTuyChonDonHang (
                            ma_mat_hang_don_hang, ma_gia_tri, ten_loai_tuy_chon,
                            ten_gia_tri, gia_them
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        ma_mat_hang_don_hang, tuy_chon['ma_gia_tri'],
                        tuy_chon['ten_loai'], tuy_chon['ten_gia_tri'], tuy_chon['gia_them']
                    ))

            elif mat_hang['loai_mat_hang'] == 'combo':
                # Chi tiết combo
                cursor.execute("""
                    SELECT 
                        ctcgh.ma_chi_tiet_combo,
                        ctc.ma_san_pham,
                        ctc.ten_san_pham,
                        ctc.so_luong,
                        ctc.gia_san_pham
                    FROM ChiTietComboGioHang ctcgh
                    JOIN ChiTietCombo ctc ON ctcgh.ma_chi_tiet_combo = ctc.ma_chi_tiet_combo
                    WHERE ctcgh.ma_mat_hang_gio_hang = %s
                """, (mat_hang['ma_mat_hang_gio_hang'],))
                
                chi_tiet_combo_list = cursor.fetchall()
                
                for ctc in chi_tiet_combo_list:
                    cursor.execute("""
                        INSERT INTO ChiTietComboDonHang (
                            ma_mat_hang_don_hang, ma_san_pham, ten_san_pham,
                            so_luong, don_gia
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        ma_mat_hang_don_hang, ctc['ma_san_pham'], ctc['ten_san_pham'],
                        ctc['so_luong'], ctc['gia_san_pham']
                    ))
                    
                    ma_chi_tiet_combo_don_hang = cursor.lastrowid
                    
                    # Tùy chọn combo
                    cursor.execute("""
                        SELECT 
                            tccgh.ma_gia_tri,
                            tccgh.gia_them,
                            gtc.ten_gia_tri,
                            ltc.ten_loai
                        FROM TuyChonComboGioHang tccgh
                        JOIN ChiTietComboGioHang ctcgh ON tccgh.ma_chi_tiet_combo_gio_hang = ctcgh.ma_chi_tiet
                        JOIN GiaTriTuyChon gtc ON tccgh.ma_gia_tri = gtc.ma_gia_tri
                        JOIN LoaiTuyChon ltc ON gtc.ma_loai_tuy_chon = ltc.ma_loai_tuy_chon
                        WHERE ctcgh.ma_mat_hang_gio_hang = %s AND ctcgh.ma_chi_tiet_combo = %s
                    """, (mat_hang['ma_mat_hang_gio_hang'], ctc['ma_chi_tiet_combo']))
                    
                    tuy_chon_combo_list = cursor.fetchall()
                    
                    for tuy_chon in tuy_chon_combo_list:
                        cursor.execute("""
                            INSERT INTO TuyChonComboDonHang (
                                ma_chi_tiet_combo_don_hang, ma_gia_tri, ten_loai_tuy_chon,
                                ten_gia_tri, gia_them
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            ma_chi_tiet_combo_don_hang, tuy_chon['ma_gia_tri'],
                            tuy_chon['ten_loai'], tuy_chon['ten_gia_tri'], tuy_chon['gia_them']
                        ))

        # 11. Cập nhật số lần sử dụng mã giảm giá
        if request.ma_giam_gia:
            cursor.execute("""
                UPDATE MaGiamGia 
                SET da_su_dung = da_su_dung + 1 
                WHERE ma_giam_gia = %s
            """, (request.ma_giam_gia,))

        # 12. Xóa giỏ hàng sau khi đặt hàng thành công
        cursor.execute("DELETE FROM MatHangGioHang WHERE ma_gio_hang = %s", (ma_gio_hang,))

        # 13. Tạo giao dịch thanh toán
        cursor.execute("""
            INSERT INTO GiaoDich (
                ma_nguoi_dung, loai_giao_dich, so_tien, trang_thai, phuong_thuc_thanh_toan
            ) VALUES (%s, %s, %s, %s, %s)
        """, (
            request.ma_nguoi_dung, 'thanh_toan_don_hang', tong_tien_cuoi_cung,
            'cho_xu_ly', request.phuong_thuc_thanh_toan
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "message": "Đặt hàng thành công",
            "ma_don_hang": ma_don_hang,
            "tong_tien_san_pham": tong_tien_san_pham,
            "phi_giao_hang": phi_giao_hang,
            "giam_gia_ma_giam_gia": giam_gia_ma_giam_gia,
            "tong_tien_cuoi_cung": tong_tien_cuoi_cung,
            "trang_thai": "da_nhan",
            "phuong_thuc_thanh_toan": request.phuong_thuc_thanh_toan
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/chiTietDonHang/{ma_don_hang}")
def get_chi_tiet_don_hang(ma_don_hang: int):
    """Lấy chi tiết đơn hàng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # Lấy thông tin đơn hàng
        cursor.execute("""
            SELECT 
                dh.*,
                nd.ho_ten,
                nd.email,
                tc.ten_cua_hang,
                tc.dia_chi as dia_chi_cua_hang,
                mgv.ma_code as ma_giam_gia_code
            FROM DonHang dh
            LEFT JOIN NguoiDung nd ON dh.ma_nguoi_dung = nd.ma_nguoi_dung
            LEFT JOIN ThongTinCuaHang tc ON dh.ma_cua_hang = tc.ma_cua_hang
            LEFT JOIN MaGiamGia mgv ON dh.ma_giam_gia = mgv.ma_giam_gia
            WHERE dh.ma_don_hang = %s
        """, (ma_don_hang,))
        
        don_hang = cursor.fetchone()
        
        if not don_hang:
            raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại")

        # Lấy các mặt hàng trong đơn hàng
        cursor.execute("""
            SELECT 
                mhdh.*,
                sp.ten_san_pham,
                sp.hinh_anh,
                c.ten_combo,
                c.hinh_anh as hinh_anh_combo
            FROM MatHangDonHang mhdh
            LEFT JOIN SanPham sp ON mhdh.ma_san_pham = sp.ma_san_pham
            LEFT JOIN Combo c ON mhdh.ma_combo = c.ma_combo
            WHERE mhdh.ma_don_hang = %s
        """, (ma_don_hang,))
        
        mat_hang_list = cursor.fetchall()

        # Lấy chi tiết tùy chọn cho từng mặt hàng
        for mat_hang in mat_hang_list:
            if mat_hang['loai_mat_hang'] == 'san_pham':
                # Tùy chọn sản phẩm đơn lẻ
                cursor.execute("""
                    SELECT * FROM ChiTietTuyChonDonHang 
                    WHERE ma_mat_hang_don_hang = %s
                """, (mat_hang['ma_mat_hang_don_hang'],))
                
                mat_hang['tuy_chon'] = cursor.fetchall()
                
            elif mat_hang['loai_mat_hang'] == 'combo':
                # Chi tiết combo
                cursor.execute("""
                    SELECT * FROM ChiTietComboDonHang 
                    WHERE ma_mat_hang_don_hang = %s
                """, (mat_hang['ma_mat_hang_don_hang'],))
                
                chi_tiet_combo = cursor.fetchall()
                
                # Tùy chọn cho từng sản phẩm trong combo
                for ctc in chi_tiet_combo:
                    cursor.execute("""
                        SELECT * FROM TuyChonComboDonHang 
                        WHERE ma_chi_tiet_combo_don_hang = %s
                    """, (ctc['ma_chi_tiet'],))
                    
                    ctc['tuy_chon'] = cursor.fetchall()
                
                mat_hang['chi_tiet_combo'] = chi_tiet_combo

        cursor.close()
        conn.close()

        return {
            "don_hang": don_hang,
            "mat_hang": mat_hang_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.get("/danhSachDonHang/{ma_nguoi_dung}")
def get_danh_sach_don_hang(ma_nguoi_dung: int, trang_thai: Optional[str] = None):
    """Lấy danh sách đơn hàng của người dùng"""
    try:
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor(dictionary=True)

        # Câu truy vấn có điều kiện
        query = """
            SELECT 
                dh.ma_don_hang,
                dh.tong_tien_cuoi_cung,
                dh.trang_thai,
                dh.dia_chi_giao_hang,
                dh.phuong_thuc_thanh_toan,
                dh.ngay_tao,
                dh.thoi_gian_giao_du_kien,
                COUNT(mhdh.ma_mat_hang_don_hang) as so_mat_hang
            FROM DonHang dh
            LEFT JOIN MatHangDonHang mhdh ON dh.ma_don_hang = mhdh.ma_don_hang
            WHERE dh.ma_nguoi_dung = %s
        """
        
        params = [ma_nguoi_dung]
        
        if trang_thai:
            query += " AND dh.trang_thai = %s"
            params.append(trang_thai)
        
        query += """
            GROUP BY dh.ma_don_hang
            ORDER BY dh.ngay_tao DESC
        """

        cursor.execute(query, tuple(params))
        don_hang_list = cursor.fetchall()

        cursor.close()
        conn.close()

        return {
            "danh_sach_don_hang": don_hang_list,
            "tong_so_don_hang": len(don_hang_list)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

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

class CapNhatGioHangRequest(BaseModel):
    so_luong: int
    ghi_chu: Optional[str] = None
    tuy_chon: Optional[List[TuyChonRequest]] = []
    chi_tiet_combo: Optional[List[ChiTietComboRequest]] = []

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

@app.get("/banner-hoat-dong")
def get_active_banners():
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            today = date.today().isoformat()

            sql = """
                SELECT ma_banner, url_hinh_anh, ma_san_pham, tieu_de, mo_ta, link_chuyen_huong,
                       ngay_bat_dau, ngay_ket_thuc, thu_tu_hien_thi, hoat_dong
                FROM Banner
                WHERE hoat_dong = 1
                  AND ngay_bat_dau <= %s
                  AND ngay_ket_thuc >= %s
                ORDER BY thu_tu_hien_thi ASC
            """
            cursor.execute(sql, (today, today))
            banners = cursor.fetchall()

            cursor.close()
            conn.close()

            return banners  # Retrofit expect List<Banner>

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

@app.put("/updateSanPham")
def update_san_pham(
    ma_san_pham: int = Form(...),
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
        # Kết nối DB
        conn = db.connect_to_database()
        if isinstance(conn, Error):
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")

        cursor = conn.cursor()

        # Lấy dữ liệu hiện tại của sản phẩm
        cursor.execute("SELECT * FROM SanPham WHERE ma_san_pham = %s", (ma_san_pham,))
        san_pham = cursor.fetchone()

        if not san_pham:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm")

        # Lấy tên các cột để sử dụng lại
        column_names = [desc[0] for desc in cursor.description]
        san_pham_dict = dict(zip(column_names, san_pham))

        # Nếu có ảnh mới thì xử lý lưu ảnh
        if hinh_anh:
            filename = f"{(ten_san_pham or san_pham_dict['ten_san_pham']).strip().replace(' ', '_')}_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"
        else:
            hinh_anh_path = san_pham_dict["hinh_anh"]

        # Cập nhật thông tin mới (nếu có), giữ nguyên nếu không truyền
        update_fields = {
            "ten_san_pham": ten_san_pham or san_pham_dict["ten_san_pham"],
            "gia_co_ban": gia_co_ban if gia_co_ban is not None else san_pham_dict["gia_co_ban"],
            "mo_ta": mo_ta if mo_ta is not None else san_pham_dict["mo_ta"],
            "ma_danh_muc": ma_danh_muc if ma_danh_muc is not None else san_pham_dict["ma_danh_muc"],
            "loai_san_pham": loai_san_pham or san_pham_dict["loai_san_pham"],
            "hien_thi": hien_thi if hien_thi is not None else san_pham_dict["hien_thi"],
            "moi": moi if moi is not None else san_pham_dict["moi"],
            "hinh_anh": hinh_anh_path
        }

        # Thực hiện update
        sql = """
            UPDATE SanPham
            SET ten_san_pham = %s, gia_co_ban = %s, mo_ta = %s,
                ma_danh_muc = %s, loai_san_pham = %s, hien_thi = %s,
                moi = %s, hinh_anh = %s
            WHERE ma_san_pham = %s
        """
        values = (
            update_fields["ten_san_pham"],
            update_fields["gia_co_ban"],
            update_fields["mo_ta"],
            update_fields["ma_danh_muc"],
            update_fields["loai_san_pham"],
            update_fields["hien_thi"],
            update_fields["moi"],
            update_fields["hinh_anh"],
            ma_san_pham
        )

        cursor.execute(sql, values)
        conn.commit()

        cursor.close()
        conn.close()

        return {
            "message": "Cập nhật sản phẩm thành công",
            "ma_san_pham": ma_san_pham,
            "du_lieu_moi": update_fields
        }

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

@app.post("/themBanner")
def add_banner(
    ngay_ket_thuc: str = Form(...),  # vẫn để client chọn
    ma_san_pham: int = Form(None),
    tieu_de: str = Form(None),
    mo_ta: str = Form(None),
    link_chuyen_huong: str = Form(None),
    thu_tu_hien_thi: int = Form(0),
    hoat_dong: bool = Form(True),
    hinh_anh: UploadFile = File(...)
):
    try:
        # Lấy ngày hôm nay
        ngay_bat_dau = date.today().isoformat()  # yyyy-mm-dd

        # Xử lý lưu ảnh
        hinh_anh_path = None
        if hinh_anh:
            filename = f"banner_{hinh_anh.filename}"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            with open(save_path, "wb") as buffer:
                shutil.copyfileobj(hinh_anh.file, buffer)

            hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

        # Kết nối CSDL và thêm banner
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO Banner (url_hinh_anh, ma_san_pham, tieu_de, mo_ta, link_chuyen_huong, 
                                    ngay_bat_dau, ngay_ket_thuc, thu_tu_hien_thi, hoat_dong) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            adr = (
                hinh_anh_path,
                ma_san_pham,
                tieu_de,
                mo_ta,
                link_chuyen_huong,
                ngay_bat_dau,
                ngay_ket_thuc,
                thu_tu_hien_thi,
                hoat_dong
            )

            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "message": "Thêm banner thành công.",
                "ngay_bat_dau": ngay_bat_dau,
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

@app.post("/themTuyChonComboGioHang")
def add_tuy_chon_combo_gio_hang(
    ma_chi_tiet_combo_gio_hang: int,
    ma_gia_tri: int,
    gia_them: float,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO TuyChonComboGioHang (ma_chi_tiet_combo_gio_hang, ma_gia_tri, gia_them) 
            VALUES (%s, %s, %s)
        """
        adr = (ma_chi_tiet_combo_gio_hang, ma_gia_tri, gia_them)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm tùy chọn combo giỏ hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm tùy chọn combo giỏ hàng thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themChiTietComboGioHang")
def add_chi_tiet_combo_gio_hang(
    ma_mat_hang_gio_hang: int,
    ma_chi_tiet_combo: int,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChiTietComboGioHang (ma_mat_hang_gio_hang, ma_chi_tiet_combo) 
            VALUES (%s, %s)
        """
        adr = (ma_mat_hang_gio_hang, ma_chi_tiet_combo)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chi tiết combo giỏ hàng thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chi tiết combo giỏ hàng thất bại: " + str(e)}
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

@app.post("/themChiTietCombo")
def add_chi_tiet_combo(
    ma_combo: int,
    ma_san_pham: int,
    so_luong: int,
    ten_san_pham: str,
    gia_san_pham: float,
    co_the_thay_the: bool = False,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ChiTietCombo (ma_combo, ma_san_pham, so_luong, ten_san_pham, gia_san_pham, co_the_thay_the) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        adr = (ma_combo, ma_san_pham, so_luong, ten_san_pham, gia_san_pham, co_the_thay_the)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm chi tiết combo thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm chi tiết combo thất bại: " + str(e)}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

@app.post("/themCombo")
def add_combo(
    ten_combo: str,
     gia_ban: float,
    gia_goc: float,
    ngay_bat_dau: str,
    ngay_ket_thuc: str,
    mo_ta: str = None,
    hinh_anh: str = None,
    so_luong_ban: int = 0,
    moi: bool = False,
    noi_bat: bool = False,
    hoat_dong: bool = True,
):
    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO Combo (ten_combo, mo_ta, hinh_anh, gia_ban, gia_goc, 
                               ngay_bat_dau, ngay_ket_thuc, so_luong_ban, 
                               moi, noi_bat, hoat_dong) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        adr = (ten_combo, mo_ta, hinh_anh, gia_ban, gia_goc, 
               ngay_bat_dau, ngay_ket_thuc, so_luong_ban, 
               moi, noi_bat, hoat_dong)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm combo thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm combo thất bại: " + str(e)}
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
