from fastapi import APIRouter
from pydantic import BaseModel
from db import connect_to_database
from websocket_routes import broadcast_update

router = APIRouter()

class SanPhamModel(BaseModel):
    ten_san_pham: str
    hinh_anh: str
    mo_ta: str
    gia_co_ban: float
    hien_thi: bool = True
    ma_danh_muc: int = None
    loai_san_pham: str = None
    moi: bool = False

@router.get("/san-pham")
def get_san_pham():
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM SanPham WHERE hien_thi = TRUE")
    return cursor.fetchall()

@router.post("/san-pham")
async def them_san_pham(sp: SanPhamModel):
    conn = get_db_conn()
    cursor = conn.cursor()
    sql = """
        INSERT INTO SanPham (ten_san_pham, hinh_anh, mo_ta, gia_co_ban, hien_thi, ma_danh_muc, loai_san_pham, moi)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (sp.ten_san_pham, sp.hinh_anh, sp.mo_ta, sp.gia_co_ban,
                         sp.hien_thi, sp.ma_danh_muc, sp.loai_san_pham, sp.moi))
    conn.commit()
    await broadcast_update("san_pham")
    return {"message": "Đã thêm sản phẩm"}
