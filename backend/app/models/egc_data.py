from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from models.base import Base


class EGCExperimentalData(Base):
    __tablename__ = 'egc_experimental_data'

    id = Column(Integer, primary_key=True, autoincrement=True)
    kb_id = Column(Integer, ForeignKey('knowledgebases.id', ondelete='CASCADE'), nullable=True)
    file_name = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)

    # 材料配比
    binder_type = Column(String(100))
    fly_ash_ratio = Column(Float)
    slag_ratio = Column(Float)
    metakaolin_ratio = Column(Float)
    water_binder_ratio = Column(Float)
    sand_binder_ratio = Column(Float)
    alkaline_activator_type = Column(String(100))
    naoh_molarity = Column(Float)
    na2sio3_naoh_ratio = Column(Float)
    activator_modulus = Column(Float)

    # 纤维信息
    fiber_type = Column(String(50))
    fiber_content_vol = Column(Float)
    fiber_length = Column(Float)
    fiber_diameter = Column(Float)
    fiber_tensile_strength = Column(Float)
    fiber_elastic_modulus = Column(Float)

    # 养护条件
    curing_age_days = Column(Integer)
    curing_temperature = Column(Float)
    curing_method = Column(String(100))

    # 力学性能
    compressive_strength_mpa = Column(Float)
    ultimate_tensile_strain_pct = Column(Float)
    flexural_strength_mpa = Column(Float)
    elastic_modulus_gpa = Column(Float)
    tensile_strength_mpa = Column(Float)
    fracture_energy_kj_m2 = Column(Float)

    # 耐久性
    chloride_penetration_coefficient = Column(Float)
    carbonation_depth_mm = Column(Float)
    freeze_thaw_resistance_cycles = Column(Integer)

    # 元数据
    test_method = Column(String(200))
    remarks = Column(Text)
    extracted_by = Column(String(50), default='llm')
    confidence_score = Column(Float)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now())

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
