from fastapi import APIRouter, Depends, HTTPException
import csv
import json
import logging
from sqlalchemy.orm import Session
from utils.database import get_db
from models.message import KnowledgeBase  
from schemas.message import FilestResponse, SessionListResponse, SessionResponse
from typing import List
from sqlalchemy import text ,select 

router = APIRouter()
logger = logging.getLogger(__name__)


def _parse_recommended_questions(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except (TypeError, json.JSONDecodeError):
        pass

    legacy_value = str(value).strip().strip("{}")
    if not legacy_value:
        return []
    return [item.strip().strip('"') for item in next(csv.reader([legacy_value])) if item.strip()]

############################
#   获取文档列表
############################

@router.get("/get_files/", response_model=List[FilestResponse])
def get_documents_by_user_id(
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    try:
        user_id = "1"

        # 构建查询语句
        stmt = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id)
        
        # 执行查询
        result = db.execute(stmt).scalars().all()
        logger.debug("Loaded %s repository documents for user %s", len(result), user_id)

        # 如果没有找到文档，返回空列表
        if not result:
            return []

        # 将查询结果转换为 Pydantic 模型
        documents = [
            FilestResponse(
                user_id=row.user_id,
                file_name=row.file_name,
                created_at=row.created_at.isoformat(),
                updated_at=row.updated_at.isoformat()
            )
            for row in result
        ]

        return documents

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 删除文件接口
@router.delete("/delete_file/", status_code=200)
def delete_file_by_name(
    file_name: str,  # 用户传入的文件名称
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    try:
        # 硬编码的用户 ID
        user_id = "1"

        # 构建查询语句：查找符合条件的记录
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.file_name == file_name
        )

        # 执行查询
        result = db.execute(stmt).scalars().first()

        # 如果没有找到对应的记录，返回 404 错误
        if not result:
            raise HTTPException(status_code=404, detail="File not found")

        # 删除记录
        db.delete(result)
        db.commit()  # 提交事务

        # 返回成功消息
        return {"message": "File deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # 捕获异常并返回 500 错误
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get_messages/")
def get_messages_by_session_id(
    session_id: str,
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    try:
        user_id = "1"

        # 查询 messages 表中对应 session_id 的消息
        messages_data = db.execute(
            text(
                "SELECT m.message_id, m.session_id, m.user_question, m.model_answer, "
                "m.documents, m.recommended_questions, m.think, m.created_at "
                "FROM messages m JOIN sessions s ON s.session_id = m.session_id "
                "WHERE m.session_id = :session_id AND s.user_id = :user_id "
                "ORDER BY m.created_at"
            ),
            {"session_id": session_id, "user_id": user_id}
        ).fetchall()

        # 构造返回数据
        messages = []
        for message in messages_data:
            recommended_questions = _parse_recommended_questions(message.recommended_questions)
            messages.append(
                {
                    "message_id": message.message_id,
                    "session_id": message.session_id,
                    "user_question": message.user_question,
                    "model_answer":message.model_answer,
                    "documents" : message.documents,
                    "recommended_questions" : recommended_questions,
                    "think" : message.think,
                    "created_at": message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            )

        return messages

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve messages: {str(e)}"
        )
    
@router.get("/get_sessions/", response_model=SessionListResponse)
def get_sessions_by_user_id(
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    try:
        user_id = "1"


        # 查询 sessions 表中对应 user_id 的所有会话
        sessions_data = db.execute(
            text("SELECT * FROM sessions WHERE user_id = :user_id ORDER BY updated_at DESC"),
            {"user_id": user_id}
        ).fetchall()

        # 构造返回数据
        sessions = []
        for session in sessions_data:
            sessions.append(
                SessionResponse(
                    session_id=session.session_id,
                    session_name=session.session_name,
                    user_id=session.user_id,
                    created_at=session.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    updated_at=session.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                )
            )

        return {"user_id": user_id, "sessions": sessions}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/delete_session/")
def delete_session(
    session_id: str,
    # credentials: JwtAuthorizationCredentials = Security(access_security),
    db: Session = Depends(get_db)
):
    """
    删除指定会话及其所有消息
    """
    try:
        user_id = "1"

        owned_session = db.execute(
            text("SELECT session_id FROM sessions WHERE session_id = :session_id AND user_id = :user_id"),
            {"session_id": session_id, "user_id": user_id}
        ).fetchone()
        if not owned_session:
            raise HTTPException(
                status_code=404,
                detail="会话不存在或无权删除"
            )

        db.execute(
            text("DELETE FROM messages WHERE session_id = :session_id"),
            {"session_id": session_id}
        )
        db.execute(
            text("DELETE FROM sessions WHERE session_id = :session_id AND user_id = :user_id"),
            {"session_id": session_id, "user_id": user_id}
        )

        db.commit()
        return {"status": "success", "message": "会话已删除"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除会话失败: {str(e)}"
        )
