from sqlalchemy import text, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from utils.database import get_db
from models.egc_data import EGCExperimentalData
from models.message import KnowledgeBase
from schemas.egc import ExperimentalDataFilter
from typing import Optional, List
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


def insert_experimental_data(data: dict) -> Optional[int]:
    """插入单条实验数据"""
    db = next(get_db())
    try:
        row = EGCExperimentalData(**data)
        db.add(row)
        db.commit()
        db.refresh(row)
        logger.info(f"Inserted experimental data id={row.id}")
        return row.id
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to insert experimental data: {e}")
        return None
    finally:
        db.close()


def bulk_insert_experimental_data(rows: List[dict]) -> List[int]:
    """批量插入实验数据"""
    db = next(get_db())
    ids = []
    try:
        for data in rows:
            row = EGCExperimentalData(**data)
            db.add(row)
            db.flush()
            ids.append(row.id)
        db.commit()
        logger.info(f"Bulk inserted {len(ids)} experimental data rows")
        return ids
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Bulk insert failed: {e}")
        return []
    finally:
        db.close()


def query_experimental_data(filters: ExperimentalDataFilter) -> dict:
    """按条件查询实验数据"""
    db = next(get_db())
    try:
        query = db.query(EGCExperimentalData)

        if filters.fiber_type:
            query = query.filter(EGCExperimentalData.fiber_type == filters.fiber_type)
        if filters.binder_type:
            query = query.filter(EGCExperimentalData.binder_type == filters.binder_type)
        if filters.compressive_strength_min is not None:
            query = query.filter(EGCExperimentalData.compressive_strength_mpa >= filters.compressive_strength_min)
        if filters.compressive_strength_max is not None:
            query = query.filter(EGCExperimentalData.compressive_strength_mpa <= filters.compressive_strength_max)
        if filters.ultimate_tensile_strain_min is not None:
            query = query.filter(EGCExperimentalData.ultimate_tensile_strain_pct >= filters.ultimate_tensile_strain_min)
        if filters.ultimate_tensile_strain_max is not None:
            query = query.filter(EGCExperimentalData.ultimate_tensile_strain_pct <= filters.ultimate_tensile_strain_max)
        if filters.water_binder_ratio_min is not None:
            query = query.filter(EGCExperimentalData.water_binder_ratio >= filters.water_binder_ratio_min)
        if filters.water_binder_ratio_max is not None:
            query = query.filter(EGCExperimentalData.water_binder_ratio <= filters.water_binder_ratio_max)
        if filters.curing_age_days is not None:
            query = query.filter(EGCExperimentalData.curing_age_days == filters.curing_age_days)

        total = query.count()
        rows = query.offset(filters.offset).limit(filters.limit).all()

        return {
            "total": total,
            "data": [row.to_dict() for row in rows]
        }
    except SQLAlchemyError as e:
        logger.error(f"Query experimental data failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")
    finally:
        db.close()


def get_similar_mixes(mix_params: dict, top_k: int = 10) -> List[dict]:
    """按关键配比参数查找相似实验数据

    相似度策略：优先匹配 fiber_type 和 binder_type，
    然后按 water_binder_ratio 的差值排序。
    """
    db = next(get_db())
    try:
        query = db.query(EGCExperimentalData)

        fiber_type = mix_params.get('fiber_type')
        binder_type = mix_params.get('binder_type')
        wb_ratio = mix_params.get('water_binder_ratio')

        if fiber_type:
            query = query.filter(EGCExperimentalData.fiber_type == fiber_type)

        if binder_type:
            query = query.filter(EGCExperimentalData.binder_type == binder_type)

        if wb_ratio is not None:
            # 允许 ±30% 范围
            low = wb_ratio * 0.7
            high = wb_ratio * 1.3
            query = query.filter(
                and_(
                    EGCExperimentalData.water_binder_ratio >= low,
                    EGCExperimentalData.water_binder_ratio <= high
                )
            )

        rows = query.order_by(
            EGCExperimentalData.compressive_strength_mpa.desc()
        ).limit(top_k).all()

        return [row.to_dict() for row in rows]
    except SQLAlchemyError as e:
        logger.error(f"Get similar mixes failed: {e}")
        return []
    finally:
        db.close()


def update_paper_metadata(kb_id: int, metadata: dict) -> bool:
    """更新论文元数据"""
    db = next(get_db())
    try:
        update_fields = {}
        allowed = ['paper_title', 'authors', 'journal', 'publication_year',
                   'doi', 'abstract', 'extraction_status']
        for k in allowed:
            if k in metadata and metadata[k] is not None:
                update_fields[k] = metadata[k]

        if update_fields:
            db.execute(
                text("UPDATE knowledgebases SET " +
                     ", ".join(f"{k} = :{k}" for k in update_fields) +
                     " WHERE id = :kb_id"),
                {**update_fields, "kb_id": kb_id}
            )
            db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Update paper metadata failed for kb_id={kb_id}: {e}")
        return False
    finally:
        db.close()


def update_extraction_status(kb_id: int, status: str) -> bool:
    """更新论文元数据提取状态"""
    return update_paper_metadata(kb_id, {"extraction_status": status})


def get_paper_metadata(kb_id: int) -> Optional[dict]:
    """获取论文元数据"""
    db = next(get_db())
    try:
        row = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if row:
            return {
                "id": row.id,
                "file_name": row.file_name,
                "paper_title": row.paper_title,
                "authors": row.authors,
                "journal": row.journal,
                "publication_year": row.publication_year,
                "doi": row.doi,
                "abstract": row.abstract,
                "file_type": row.file_type,
                "extraction_status": row.extraction_status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        return None
    except SQLAlchemyError as e:
        logger.error(f"Get paper metadata failed: {e}")
        return None
    finally:
        db.close()
