from fastapi import File, UploadFile, FastAPI, HTTPException, Form, Path
import os, shutil
from typing import Literal
from mysql.connector import Error
import db
from fastapi.responses import JSONResponse

app = FastAPI()

from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_FOLDER = "static/images/avatar"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

from fastapi import UploadFile, File

@app.put("/danhmuc/{ma_danh_muc}")
def update_danh_muc(
    ma_danh_muc: int = Path(..., gt=0),
    ten_danh_muc: str = Form(...),
    mo_ta: str = Form(None),
    thu_tu_hien_thi: int = Form(0),
    hoat_dong: bool = Form(True),
    hinh_anh: UploadFile = File(None)
):
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor(dictionary=True)

            # Kiểm tra danh mục có tồn tại
            cursor.execute("SELECT * FROM DanhMuc WHERE ma_danh_muc = %s", (ma_danh_muc,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")

            # Xử lý ảnh nếu có upload mới
            hinh_anh_path = existing["hinh_anh"]
            if hinh_anh:
                filename = f"{ten_danh_muc.strip().replace(' ', '_')}_{hinh_anh.filename}"
                save_path = os.path.join(CATEGORY_FOLDER, filename)
                with open(save_path, "wb") as buffer:
                    shutil.copyfileobj(hinh_anh.file, buffer)
                hinh_anh_path = f"/{save_path.replace(os.sep, '/')}"

            # Cập nhật
            sql = """
                UPDATE DanhMuc
                SET ten_danh_muc = %s,
                    hinh_anh = %s,
                    mo_ta = %s,
                    thu_tu_hien_thi = %s,
                    hoat_dong = %s
                WHERE ma_danh_muc = %s
            """
            values = (
                ten_danh_muc,
                hinh_anh_path,
                mo_ta,
                thu_tu_hien_thi,
                hoat_dong,
                ma_danh_muc
            )
            cursor.execute(sql, values)
            conn.commit()

            cursor.close()
            conn.close()
            return {"message": "Cập nhật danh mục thành công"}
        else:
            raise HTTPException(status_code=500, detail="Lỗi kết nối cơ sở dữ liệu")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi server: {str(e)}")

@app.delete("/danhmuc/{ma_danh_muc}")
def delete_danh_muc(ma_danh_muc: int = Path(..., gt=0)):
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
                INSERT INTO NguoiDung (email, so_dien_thoai, mat_khau, vai_tro, ho_ten, anh_dai_dien, hoat_dong)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
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
    
@app.get("/getAllDanhMuc")
def get_all_danh_muc():
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