from sqlalchemy import Column, String, Text, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from models.base import Base

class Message(Base):
    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    session_id = Column(String(16), nullable=False)
    user_question = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    documents = Column(Text)
    recommended_questions = Column(Text)
    think = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

class KnowledgeBase(Base):
    __tablename__ = 'knowledgebases'  # 表名

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键
    user_id = Column(String(255), nullable=False)  # 用户 ID
    file_name = Column(String(255), nullable=False)  # 文件名称
    paper_title = Column(String(500))  # 论文标题
    authors = Column(Text)  # 作者列表
    journal = Column(String(300))  # 期刊/会议名
    publication_year = Column(Integer)  # 发表年份
    doi = Column(String(200))  # DOI
    abstract = Column(Text)  # 摘要
    file_type = Column(String(20), default='paper')  # 文件类型：paper / dataset
    extraction_status = Column(String(20), default='pending')  # 提取状态：pending/processing/completed/failed
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 创建时间
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())  # 更新时间
