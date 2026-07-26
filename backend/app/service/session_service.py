from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid

class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: str, session_name: str = "New session"):
        try:
            session_id = str(uuid.uuid4()).replace("-", "")[:16]

            # 插入会话记录
            self.db.execute(
                text("""
                INSERT INTO sessions (session_id, user_id, session_name)
                VALUES (:session_id, :user_id, :session_name)
                """),
                {"session_id": session_id, "user_id": user_id, "session_name": session_name}
            )
            self.db.commit()

            return {
                "session_id": session_id,
                "status": "success",
                "message": "Session created successfully"
            }
        except Exception as e:
            self.db.rollback()
            raise e

# 服务实例化
def get_session_service(db: Session):
    return SessionService(db)
