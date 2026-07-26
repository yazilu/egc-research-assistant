from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# 配比输入 (Mix Design Input)
# ============================================================

class MixDesignRequest(BaseModel):
    """用户输入的 EGC 材料配比参数，所有字段可选"""
    # 材料配比
    binder_type: Optional[str] = None
    fly_ash_ratio: Optional[float] = None
    slag_ratio: Optional[float] = None
    metakaolin_ratio: Optional[float] = None
    water_binder_ratio: Optional[float] = None
    sand_binder_ratio: Optional[float] = None
    alkaline_activator_type: Optional[str] = None
    naoh_molarity: Optional[float] = None
    na2sio3_naoh_ratio: Optional[float] = None
    activator_modulus: Optional[float] = None

    # 纤维信息
    fiber_type: Optional[str] = None
    fiber_content_vol: Optional[float] = None
    fiber_length: Optional[float] = None
    fiber_diameter: Optional[float] = None
    fiber_tensile_strength: Optional[float] = None
    fiber_elastic_modulus: Optional[float] = None

    # 养护条件
    curing_age_days: Optional[int] = None
    curing_temperature: Optional[float] = None
    curing_method: Optional[str] = None


# ============================================================
# 预测结果 (Prediction Result)
# ============================================================

class PropertyPrediction(BaseModel):
    """单个力学性能的预测结果"""
    value: Optional[float] = None
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    confidence: Optional[float] = None  # 0-1
    unit: str = ""


class Reference(BaseModel):
    """预测所依据的参考文献"""
    title: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None


class PredictionResponse(BaseModel):
    """力学性能预测的完整响应"""
    compressive_strength: Optional[PropertyPrediction] = None
    ultimate_tensile_strain: Optional[PropertyPrediction] = None
    flexural_strength: Optional[PropertyPrediction] = None
    elastic_modulus: Optional[PropertyPrediction] = None
    tensile_strength: Optional[PropertyPrediction] = None
    fracture_energy: Optional[PropertyPrediction] = None

    similar_experiments: List[dict] = Field(default_factory=list)  # 相似配比的实验数据
    references: List[Reference] = Field(default_factory=list)
    summary: str = ""  # LLM 生成的综合分析
    status: str = "success"
    message: str = ""


# ============================================================
# 优化请求与结果 (Mix Optimization)
# ============================================================

class OptimizationTarget(BaseModel):
    """优化目标：用户希望达到的力学性能"""
    compressive_strength_min: Optional[float] = None   # MPa
    compressive_strength_max: Optional[float] = None
    ultimate_tensile_strain_min: Optional[float] = None  # %
    ultimate_tensile_strain_max: Optional[float] = None
    flexural_strength_min: Optional[float] = None
    flexural_strength_max: Optional[float] = None
    elastic_modulus_min: Optional[float] = None


class OptimizationRequest(BaseModel):
    target: OptimizationTarget
    constraints: Optional[MixDesignRequest] = None  # 可选的约束条件（如限制纤维类型）


class OptimizationSuggestion(BaseModel):
    """单个配比参数的建议值"""
    parameter: str
    suggested_range: str
    rationale: str


class OptimizationResponse(BaseModel):
    """配比优化建议的完整响应"""
    suggestions: List[OptimizationSuggestion] = Field(default_factory=list)
    expected_improvement: str = ""  # 预期改善幅度
    trade_offs: str = ""  # 权衡分析
    references: List[Reference] = Field(default_factory=list)
    status: str = "success"
    message: str = ""


# ============================================================
# 实验数据查询 (Experimental Data Query)
# ============================================================

class ExperimentalDataFilter(BaseModel):
    """结构化实验数据的筛选条件"""
    fiber_type: Optional[str] = None
    binder_type: Optional[str] = None
    compressive_strength_min: Optional[float] = None
    compressive_strength_max: Optional[float] = None
    ultimate_tensile_strain_min: Optional[float] = None
    ultimate_tensile_strain_max: Optional[float] = None
    water_binder_ratio_min: Optional[float] = None
    water_binder_ratio_max: Optional[float] = None
    curing_age_days: Optional[int] = None
    limit: int = 20
    offset: int = 0


class ExperimentalDataResponse(BaseModel):
    """单条实验数据"""
    id: int
    kb_id: Optional[int] = None
    file_name: Optional[str] = None
    binder_type: Optional[str] = None
    fly_ash_ratio: Optional[float] = None
    slag_ratio: Optional[float] = None
    water_binder_ratio: Optional[float] = None
    sand_binder_ratio: Optional[float] = None
    alkaline_activator_type: Optional[str] = None
    naoh_molarity: Optional[float] = None
    na2sio3_naoh_ratio: Optional[float] = None
    fiber_type: Optional[str] = None
    fiber_content_vol: Optional[float] = None
    fiber_length: Optional[float] = None
    curing_age_days: Optional[int] = None
    curing_temperature: Optional[float] = None
    curing_method: Optional[str] = None
    compressive_strength_mpa: Optional[float] = None
    ultimate_tensile_strain_pct: Optional[float] = None
    flexural_strength_mpa: Optional[float] = None
    elastic_modulus_gpa: Optional[float] = None
    tensile_strength_mpa: Optional[float] = None
    fracture_energy_kj_m2: Optional[float] = None
    test_method: Optional[str] = None
    remarks: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: Optional[str] = None


class ExperimentalDataListResponse(BaseModel):
    """实验数据列表响应"""
    total: int
    data: List[ExperimentalDataResponse]


# ============================================================
# 论文元数据 (Paper Metadata)
# ============================================================

class PaperMetadataResponse(BaseModel):
    """论文元数据"""
    id: int
    file_name: str
    paper_title: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    publication_year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    file_type: Optional[str] = None
    extraction_status: Optional[str] = None
    created_at: Optional[str] = None


class ReExtractResponse(BaseModel):
    """重新提取元数据的响应"""
    kb_id: int
    status: str
    message: str
