from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from typing import Optional
from mysql.connector import Error
import db

app = FastAPI()


@app.post("/addDanhMuc")
def add_danh_muc(
    ten_danh_muc: str = Form(...),
    hinh_anh: str = Form(None),
    mo_ta: str = Form(None),
    thu_tu_hien_thi: int = Form(0),
    hoat_dong: bool = Form(True)
):
    try:
        conn = db.connect_to_database()
        if not isinstance(conn, Error):
            cursor = conn.cursor()

            sql = """
                INSERT INTO DanhMuc (ten_danh_muc, hinh_anh, mo_ta, thu_tu_hien_thi, hoat_dong)
                VALUES (%s, %s, %s, %s, %s)
            """
            values = (
                ten_danh_muc,
                hinh_anh,
                mo_ta,
                thu_tu_hien_thi,
                hoat_dong
            )

            cursor.execute(sql, values)
            conn.commit()

            new_id = cursor.lastrowid

            cursor.close()
            conn.close()

            return {"message": "Thêm danh mục thành công", "ma_danh_muc": new_id}
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