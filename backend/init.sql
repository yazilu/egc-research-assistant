
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- 创建 users 表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);

-- 创建会话表
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(16) PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,  
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at  ON sessions(created_at);

-- 创建 messages 表
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(16) NOT NULL,
    user_question TEXT NOT NULL,
    model_answer TEXT NOT NULL,
    documents  TEXT,  -- 修改为 jsonb 类型
    recommended_questions TEXT,  
    think TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- 创建知识库表
CREATE TABLE IF NOT EXISTS knowledgebases (
    id SERIAL PRIMARY KEY,  -- 主键，自增
    user_id VARCHAR(255) NOT NULL,       -- 用户 ID
    file_name VARCHAR(255) NOT NULL,     -- 文件名称
    paper_title VARCHAR(500),            -- 论文标题
    authors TEXT,                        -- 作者列表
    journal VARCHAR(300),                -- 期刊/会议名
    publication_year INTEGER,            -- 发表年份
    doi VARCHAR(200),                    -- DOI
    abstract TEXT,                       -- 摘要
    file_type VARCHAR(20) DEFAULT 'paper', -- 文件类型：paper / dataset
    extraction_status VARCHAR(20) DEFAULT 'pending', -- 提取状态：pending/processing/completed/failed
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP  -- 更新时间
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_knowledgebases_user_id ON knowledgebases(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledgebases_created_at ON knowledgebases(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledgebases_file_type ON knowledgebases(file_type);
CREATE INDEX IF NOT EXISTS idx_knowledgebases_extraction_status ON knowledgebases(extraction_status);

-- ============================================================
-- EGC 实验数据表：存储从论文中提取的结构化力学性能数据
-- ============================================================
CREATE TABLE IF NOT EXISTS egc_experimental_data (
    id SERIAL PRIMARY KEY,
    kb_id INTEGER REFERENCES knowledgebases(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,

    -- 材料配比 (Mix Proportions)
    binder_type VARCHAR(100),              -- 胶凝材料类型：fly_ash / slag / metakaolin / blend
    fly_ash_ratio NUMERIC(5,4),            -- 粉煤灰占总胶凝材料比例 (0-1)
    slag_ratio NUMERIC(5,4),               -- 矿渣占总胶凝材料比例 (0-1)
    metakaolin_ratio NUMERIC(5,4),         -- 偏高岭土占总胶凝材料比例 (0-1)
    water_binder_ratio NUMERIC(5,4),       -- 水胶比
    sand_binder_ratio NUMERIC(6,3),        -- 砂胶比
    alkaline_activator_type VARCHAR(100),  -- 碱激发剂类型，如 NaOH+Na2SiO3
    naoh_molarity NUMERIC(5,2),            -- NaOH 浓度 (mol/L)
    na2sio3_naoh_ratio NUMERIC(5,3),       -- Na2SiO3/NaOH 质量比
    activator_modulus NUMERIC(5,3),        -- 激发剂模数 (SiO2/Na2O molar ratio)

    -- 纤维信息 (Fiber Information)
    fiber_type VARCHAR(50),                -- 纤维类型：PVA / PE / PP / steel / basalt / hybrid
    fiber_content_vol NUMERIC(6,4),        -- 纤维体积掺量 (%)
    fiber_length NUMERIC(6,2),             -- 纤维长度 (mm)
    fiber_diameter NUMERIC(6,3),           -- 纤维直径 (μm)
    fiber_tensile_strength NUMERIC(7,1),   -- 纤维抗拉强度 (MPa)
    fiber_elastic_modulus NUMERIC(7,1),    -- 纤维弹性模量 (GPa)

    -- 养护条件 (Curing Conditions)
    curing_age_days INTEGER,               -- 养护龄期 (天)
    curing_temperature NUMERIC(5,1),       -- 养护温度 (℃)
    curing_method VARCHAR(100),            -- 养护方式：ambient / heat / steam / water

    -- 力学性能 (Mechanical Properties) — 核心预测目标
    compressive_strength_mpa NUMERIC(7,2),       -- 抗压强度 (MPa)
    ultimate_tensile_strain_pct NUMERIC(6,4),    -- 极限拉伸应变 (%)
    flexural_strength_mpa NUMERIC(7,2),          -- 抗折强度 (MPa)
    elastic_modulus_gpa NUMERIC(6,2),            -- 弹性模量 (GPa)
    tensile_strength_mpa NUMERIC(7,2),           -- 抗拉强度 (MPa)
    fracture_energy_kj_m2 NUMERIC(7,3),          -- 断裂能 (kJ/m²)

    -- 耐久性 (Durability)
    chloride_penetration_coefficient NUMERIC(8,4), -- 氯离子渗透系数
    carbonation_depth_mm NUMERIC(6,3),             -- 碳化深度 (mm)
    freeze_thaw_resistance_cycles INTEGER,         -- 抗冻融循环次数

    -- 元数据
    test_method VARCHAR(200),              -- 测试方法/标准
    remarks TEXT,                          -- 备注
    extracted_by VARCHAR(50) DEFAULT 'llm', -- 提取方式：llm / manual
    confidence_score NUMERIC(3,2),         -- 提取置信度 (0-1)

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- EGC 实验数据表索引
CREATE INDEX IF NOT EXISTS idx_egc_expdata_user ON egc_experimental_data(user_id);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_kbid ON egc_experimental_data(kb_id);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_ucs ON egc_experimental_data(compressive_strength_mpa);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_uts ON egc_experimental_data(ultimate_tensile_strain_pct);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_fiber ON egc_experimental_data(fiber_type);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_binder ON egc_experimental_data(binder_type);
CREATE INDEX IF NOT EXISTS idx_egc_expdata_wb ON egc_experimental_data(water_binder_ratio);