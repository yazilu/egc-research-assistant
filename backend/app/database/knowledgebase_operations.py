from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.database import get_db  # 根据实际模块名称导入
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def insert_knowledgebase(user_id: str, file_name: str) -> int:
    """
    将知识库信息插入到 knowledgebases 表中。

    :param user_id: 用户 ID
    :param file_name: 文件名称
    """
    db = next(get_db())  # 获取数据库会话
    try:
        result = db.execute(
            text(
                """
                INSERT INTO knowledgebases (user_id, file_name)
                VALUES (:user_id, :file_name)
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "file_name": file_name
            }
        )
        db.commit()
        return result.scalar_one()
    except SQLAlchemyError as e:
        db.rollback()
        raise RuntimeError(f"Failed to insert into knowledgebases: {str(e)}")
    finally:
        db.close()

def verify_user_knowledgebase(user_id: str):
    """
    验证用户是否有自己的知识库。

    :param user_id: 用户 ID
    :return: 如果用户有知识库，返回 True；否则，返回 False
    """
    db = next(get_db())  # 获取数据库会话
    try:
        query_result = db.execute(
            text("SELECT id FROM knowledgebases WHERE user_id = :user_id LIMIT 1"),
            {"user_id": user_id}
        ).fetchone()

        if query_result:
            return True
        else:
            return False
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database operation failed: {str(e)}"
        )
    finally:
        db.close()

def get_user_history_questions(session_id: str):
    """
    获取用户的历史问题（废弃，保留兼容性）。
    """
    history = get_chat_history(session_id)
    return [h["question"] for h in history]


def get_chat_history(session_id: str, max_turns: int = 10, max_answer_chars: int = 300):
    """
    获取会话的完整对话历史（Q&A 对）。

    :param session_id: 会话 ID
    :param max_turns: 最多返回的对话轮次
    :param max_answer_chars: 每条回答最多保留的字符数
    :return: [{"question": ..., "answer": ...}, ...] 按时间顺序排列
    """
    db = next(get_db())
    try:
        messages_data = db.execute(
            text(
                "SELECT user_question, model_answer FROM messages "
                "WHERE session_id = :session_id "
                "ORDER BY created_at DESC LIMIT :max_turns"
            ),
            {"session_id": session_id, "max_turns": max_turns}
        ).fetchall()

        # 反转回时间正序
        messages_data = list(messages_data)[::-1]

        history = []
        for msg in messages_data:
            answer = msg.model_answer or ""
            if len(answer) > max_answer_chars:
                answer = answer[:max_answer_chars] + "..."
            history.append({
                "question": msg.user_question,
                "answer": answer,
            })
        return history
    except SQLAlchemyError as e:
        raise RuntimeError(f"Failed to fetch chat history: {str(e)}")
    finally:
        db.close()


def get_kb_id_by_filename(file_name: str, user_id: str) -> int | None:
    """
    根据文件名和用户 ID 获取 knowledgebase 记录的主键 ID。

    :param file_name: 文件名
    :param user_id: 用户 ID
    :return: knowledgebase 记录的 id，如果找不到则返回 None
    """
    db = next(get_db())
    try:
        query_result = db.execute(
            text("SELECT id FROM knowledgebases WHERE file_name = :file_name AND user_id = :user_id ORDER BY id DESC LIMIT 1"),
            {"file_name": file_name, "user_id": user_id}
        ).fetchone()

        if query_result:
            return query_result.id
        return None
    except SQLAlchemyError as e:
        logger.error(f"Failed to get kb_id: {e}")
        return None
    finally:
        db.close()
