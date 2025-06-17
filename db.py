import mysql.connector
from mysql.connector import Error
import config
import os
print("[DEBUG] Đang chạy trong thư mục:", os.getcwd())

def connect_to_database():
    """
    Kết nối tới cơ sở dữ liệu MySQL.
    
    Args:
        host (str): Địa chỉ máy chủ MySQL (ví dụ: 'localhost').
        database (str): Tên cơ sở dữ liệu.
        user (str): Tên người dùng MySQL.
        password (str): Mật khẩu người dùng MySQL.
    
    Returns:
        connection: Đối tượng kết nối nếu thành công, None nếu thất bại.
    """
    try:
        connection = mysql.connector.connect(
            host=config.HOST,
            user=config.USER,
            password=config.PASSWORD,
            database=config.DATABASE
        )
        if connection.is_connected():
            return connection
    except Error as e:
        return e