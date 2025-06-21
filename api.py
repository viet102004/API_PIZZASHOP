from fastapi import File, UploadFile, FastAPI, HTTPException, Form, Path
import os, shutil
from typing import Literal, Optional
from mysql.connector import Error
import db
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from websocket_routes import router as websocket_router, broadcast_update
from datetime import date

app = FastAPI()

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
    ma_san_pham: int,
    hinh_anh: UploadFile = File(...),
    thu_tu: int = 0,
):
    try:
        # Xử lý lưu ảnh
        hinh_anh_path = None
        if hinh_anh:
            filename = f"{ma_san_pham}_{hinh_anh.filename}"
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
                INSERT INTO HinhAnhSanPham (ma_san_pham, url_hinh_anh, thu_tu) 
                VALUES (%s, %s, %s)
            """
            adr = (ma_san_pham, hinh_anh_path, thu_tu)

            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm hình ảnh sản phẩm thành công."}
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")



    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM HinhAnhSanPham WHERE ma_san_pham = %s ORDER BY thu_tu ASC"
        cursor.execute(sql, (ma_san_pham,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return {"hinh_anh_san_pham": results}
    else:
        return {"message": "Lỗi kết nối cơ sở dữ liệu."}

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

@app.post("/themThongBao")
def add_thong_bao(
    ma_nguoi_dung: int,
    loai_thong_bao: str,
    noi_dung: str,
    trang_thai: str = 'cho_gui',
    da_doc: bool = False,
):
    if loai_thong_bao not in ['email', 'sms', 'push']:
        return {"message": "Loại thông báo không hợp lệ."}
    if trang_thai not in ['da_gui', 'cho_gui', 'that_bai']:
        return {"message": "Trạng thái thông báo không hợp lệ."}

    conn = db.connect_to_database()
    if not isinstance(conn, Error):
        cursor = conn.cursor()
        sql = """
            INSERT INTO ThongBao (ma_nguoi_dung, loai_thong_bao, noi_dung, trang_thai, da_doc) 
            VALUES (%s, %s, %s, %s, %s)
        """
        adr = (ma_nguoi_dung, loai_thong_bao, noi_dung, trang_thai, da_doc)

        try:
            cursor.execute(sql, adr)
            conn.commit()
            cursor.close()
            conn.close()
            return {"message": "Thêm thông báo thành công."}
        except Error as e:
            conn.close()
            return {"message": "Thêm thông báo thất bại: " + str(e)}
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