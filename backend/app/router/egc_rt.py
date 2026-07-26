"""
EGC 力学性能研究专用 API 路由

提供配比预测、配比优化、实验数据查询、论文元数据管理等接口
"""

from fastapi import APIRouter, HTTPException, Query, status
from schemas.egc import (
    MixDesignRequest,
    PredictionResponse,
    OptimizationRequest,
    OptimizationResponse,
    ExperimentalDataFilter,
    ExperimentalDataListResponse,
    ExperimentalDataResponse,
    PaperMetadataResponse,
    ReExtractResponse,
)
from database.egc_operations import (
    query_experimental_data,
    get_paper_metadata,
    update_extraction_status,
)
from service.core.egc_predictor import predict_performance, optimize_mix
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# 力学性能预测
# ============================================================

@router.post("/predict/", response_model=PredictionResponse)
def predict(
    mix_design: MixDesignRequest,
    user_id: str = Query("1", description="用户ID"),
):
    """
    输入 EGC 材料配比参数，预测力学性能。

    系统会从论文数据库中查找相似配比的实验数据，结合学术文献，
    使用 LLM 进行推理预测，返回各力学性能的预测值及置信区间。
    """
    try:
        mix_dict = mix_design.model_dump(exclude_none=True)
        if not mix_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请至少输入一项配比参数"
            )

        result = predict_performance(mix_dict, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预测失败: {str(e)}"
        )


# ============================================================
# 配比优化
# ============================================================

@router.post("/optimize/", response_model=OptimizationResponse)
def optimize(
    request: OptimizationRequest,
    user_id: str = Query("1", description="用户ID"),
):
    """
    给定目标力学性能，建议最优的 EGC 配比方案。

    系统会从数据库中查找满足或接近目标性能的配比数据，
    结合文献分析给出各参数的建议范围和原理说明。
    """
    try:
        target_dict = request.target.model_dump(exclude_none=True)
        constraints_dict = request.constraints.model_dump(exclude_none=True) if request.constraints else None

        if not target_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请至少设置一项目标性能指标"
            )

        result = optimize_mix(target_dict, constraints_dict, user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"优化失败: {str(e)}"
        )


# ============================================================
# 实验数据查询
# ============================================================

@router.get("/experimental_data/", response_model=ExperimentalDataListResponse)
def get_experimental_data(
    fiber_type: Optional[str] = Query(None, description="纤维类型: PVA/PE/PP/steel/basalt/hybrid"),
    binder_type: Optional[str] = Query(None, description="胶凝材料类型: fly_ash/slag/metakaolin/blend"),
    compressive_strength_min: Optional[float] = Query(None, description="最小抗压强度 (MPa)"),
    compressive_strength_max: Optional[float] = Query(None, description="最大抗压强度 (MPa)"),
    ultimate_tensile_strain_min: Optional[float] = Query(None, description="最小极限拉伸应变 (%)"),
    ultimate_tensile_strain_max: Optional[float] = Query(None, description="最大极限拉伸应变 (%)"),
    water_binder_ratio_min: Optional[float] = Query(None, description="最小水胶比"),
    water_binder_ratio_max: Optional[float] = Query(None, description="最大水胶比"),
    curing_age_days: Optional[int] = Query(None, description="养护龄期 (天)"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    按条件筛选从论文中提取的结构化实验数据。

    支持按纤维类型、胶凝材料类型、强度范围、拉伸应变范围、
    水胶比范围、养护龄期等多条件组合筛选。
    """
    try:
        filters = ExperimentalDataFilter(
            fiber_type=fiber_type,
            binder_type=binder_type,
            compressive_strength_min=compressive_strength_min,
            compressive_strength_max=compressive_strength_max,
            ultimate_tensile_strain_min=ultimate_tensile_strain_min,
            ultimate_tensile_strain_max=ultimate_tensile_strain_max,
            water_binder_ratio_min=water_binder_ratio_min,
            water_binder_ratio_max=water_binder_ratio_max,
            curing_age_days=curing_age_days,
            limit=limit,
            offset=offset,
        )
        result = query_experimental_data(filters)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


# ============================================================
# 论文元数据
# ============================================================

@router.get("/paper_metadata/{kb_id}", response_model=PaperMetadataResponse)
def get_paper_metadata_endpoint(
    kb_id: int,
):
    """
    获取指定论文的元数据信息（标题、作者、期刊、年份、DOI、摘要、提取状态等）。
    """
    try:
        metadata = get_paper_metadata(kb_id)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到 kb_id={kb_id} 的论文记录"
            )
        return metadata

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询论文元数据失败: {str(e)}"
        )


# ============================================================
# 重新提取论文元数据
# ============================================================

@router.post("/re_extract/{kb_id}", response_model=ReExtractResponse)
def re_extract_metadata(
    kb_id: int,
):
    """
    触发重新提取指定论文的元数据和实验数据。

    将 extraction_status 重置为 pending，后续可通过文件重新上传触发提取。
    """
    try:
        success = update_extraction_status(kb_id, "pending")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到 kb_id={kb_id} 的记录"
            )
        return ReExtractResponse(
            kb_id=kb_id,
            status="pending",
            message="已重置提取状态为 pending，重新上传文件将触发提取"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置提取状态失败: {str(e)}"
        )
