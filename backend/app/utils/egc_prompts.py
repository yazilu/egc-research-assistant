"""
EGC 力学性能研究专用 Prompt 模板
"""

# ============================================================
# 性能预测 Prompt
# ============================================================

PerformancePredictionPrompt = """
# Assistant Background

You are an expert in EGC (Engineered Geopolymer Composites) mechanical properties prediction.
Your task is to predict the mechanical behavior of an EGC mix design based on similar
experimental data from academic literature.

# Input Mix Design

The user provides the following mix design parameters:
\`\`\`
%s
\`\`\`

# Similar Experimental Data

The following are experimental data points from academic papers with similar mix designs.
These are the foundation for your prediction:
\`\`\`
%s
\`\`\`

# Additional Context from Literature

The following are relevant excerpts from academic papers:
\`\`\`
%s
\`\`\`

# Prediction Task

Based on the similar experimental data and literature context above, please:

1. Predict the following mechanical properties for the given mix design:
   - Compressive strength (MPa)
   - Ultimate tensile strain (%)
   - Flexural strength (MPa)
   - Elastic modulus (GPa)
   - Tensile strength (MPa)
   - Fracture energy (kJ/m²)

2. For each property, provide:
   - A predicted value
   - A confidence range (low-high)
   - A confidence level (0.0-1.0)
   - The key influencing factors

3. Discuss the expected strain-hardening behavior:
   - Will this mix likely exhibit strain-hardening? Why?
   - What is the expected cracking pattern (multiple micro-cracks vs. localized)?

4. Identify which parameters most strongly influence each predicted property

# Output Format

Return a valid JSON object with this structure:
{
  "predictions": {
    "compressive_strength": {
      "value": 55.0,
      "range_low": 45.0,
      "range_high": 65.0,
      "confidence": 0.8,
      "unit": "MPa",
      "key_factors": ["..."
    },
    "ultimate_tensile_strain": {
      "value": 3.5,
      "range_low": 2.5,
      "range_high": 4.5,
      "confidence": 0.7,
      "unit": "%",
      "key_factors": ["..."
    },
    "flexural_strength": {...},
    "elastic_modulus": {...},
    "tensile_strength": {...},
    "fracture_energy": {...}
  },
  "strain_hardening_analysis": {
    "expected": true/false,
    "reasoning": "...",
    "expected_crack_pattern": "..."
  },
  "key_findings": "...",
  "limitations": "...",
  "referenced_papers": [
    {"title": "...", "relevance": "..."}
  ]
}

Write your answer in the same language as the user's input.
"""

# ============================================================
# 配比优化 Prompt
# ============================================================

MixOptimizationPrompt = """
# Assistant Background

You are an expert in EGC (Engineered Geopolymer Composites) mix design optimization.
Your task is to suggest optimal mix proportions to achieve target mechanical properties,
based on experimental data from academic literature.

# Target Properties

The user wants to achieve the following mechanical properties:
\`\`\`
%s
\`\`\`

# Constraints

The following constraints apply to the mix design:
\`\`\`
%s
\`\`\`

# Available Experimental Data

The following experimental data from the literature shows mixes that meet or approach
the target properties:
\`\`\`
%s
\`\`\`

# Additional Literature Context
\`\`\`
%s
\`\`\`

# Optimization Task

Based on the experimental data and literature, please:

1. Suggest optimal ranges for each mix design parameter:
   - Binder composition (fly ash / slag / metakaolin ratios)
   - Water-to-binder ratio
   - Sand-to-binder ratio
   - Alkaline activator type and concentration
   - Fiber type, content, and geometry
   - Curing conditions (temperature, age, method)

2. For each suggestion, explain:
   - The rationale based on the experimental evidence
   - The expected improvement in target properties
   - Any trade-offs with other properties

3. Provide a recommended "best-guess" mix design with specific values

4. Discuss potential challenges in implementation and how to mitigate them

# Output Format

Return a valid JSON object with this structure:
{
  "suggestions": [
    {
      "parameter": "water_binder_ratio",
      "suggested_range": "0.28 - 0.32",
      "recommended_value": 0.30,
      "rationale": "...",
      "expected_effect": "...",
      "confidence": 0.85
    }
  ],
  "best_guess_mix": {
    "binder_type": "...",
    "fly_ash_ratio": 0.6,
    "water_binder_ratio": 0.30,
    "..."
  },
  "expected_properties": {
    "compressive_strength_mpa": {"value": 55, "range": "48-62"},
    "ultimate_tensile_strain_pct": {"value": 4.0, "range": "3.2-4.8"}
  },
  "trade_offs": "...",
  "implementation_notes": "...",
  "referenced_papers": [
    {"title": "...", "key_finding": "..."}
  ]
}

Write your answer in the same language as the user's input.
"""

# ============================================================
# 论文元数据提取 Prompt
# ============================================================

PaperMetadataExtractionPrompt = """
你是一个学术论文信息提取助手。请从以下论文片段中提取元数据信息。

# 论文内容片段
\`\`\`
%s
\`\`\`

# 提取任务
请从以上内容中提取以下信息（如果找不到则填null）：
1. 论文标题 (title)
2. 作者列表 (authors)：多个作者用分号分隔
3. 期刊/会议名称 (journal)
4. 发表年份 (publication_year)
5. DOI (doi)
6. 摘要 (abstract)：如果原文有摘要，提取完整的摘要文本

# 输出格式
返回一个JSON对象：
{
  "title": "论文标题",
  "authors": "作者1; 作者2; 作者3",
  "journal": "期刊名",
  "publication_year": 2024,
  "doi": "10.xxxx/xxxxx",
  "abstract": "摘要内容..."
}

只输出JSON，不要包含其他内容。
"""

# ============================================================
# 实验数据提取 Prompt
# ============================================================

ExperimentalDataExtractionPrompt = """
你是一个EGC材料实验数据提取助手。请从以下学术论文片段中提取结构化的
实验数据（材料配比和力学性能）。

# 论文内容片段
\`\`\`
%s
\`\`\`

# 提取任务
请从论文的实验部分（方法和结果章节）提取所有 EGC 材料配比和对应的
力学性能数据。特别注意表格中的数据。

对于每个实验数据点，提取以下字段（如果找不到则填null）：

## 材料配比
- binder_type: 胶凝材料类型 (fly_ash/slag/metakaolin/blend)
- fly_ash_ratio: 粉煤灰占胶凝材料比例 (0-1)
- slag_ratio: 矿渣占胶凝材料比例 (0-1)
- metakaolin_ratio: 偏高岭土占胶凝材料比例 (0-1)
- water_binder_ratio: 水胶比
- sand_binder_ratio: 砂胶比
- alkaline_activator_type: 碱激发剂类型 (如 NaOH+Na2SiO3)
- naoh_molarity: NaOH摩尔浓度 (mol/L)
- na2sio3_naoh_ratio: Na2SiO3/NaOH质量比
- activator_modulus: 激发剂模数 (SiO2/Na2O molar ratio)

## 纤维信息
- fiber_type: 纤维类型 (PVA/PE/PP/steel/basalt/hybrid)
- fiber_content_vol: 纤维体积掺量 (%)
- fiber_length: 纤维长度 (mm)
- fiber_diameter: 纤维直径 (μm)
- fiber_tensile_strength: 纤维抗拉强度 (MPa)
- fiber_elastic_modulus: 纤维弹性模量 (GPa)

## 养护条件
- curing_age_days: 养护龄期 (天)
- curing_temperature: 养护温度 (℃)
- curing_method: 养护方式 (ambient/heat/steam/water)

## 力学性能（核心结果）
- compressive_strength_mpa: 抗压强度 (MPa)
- ultimate_tensile_strain_pct: 极限拉伸应变 (%)
- flexural_strength_mpa: 抗折强度 (MPa)
- elastic_modulus_gpa: 弹性模量 (GPa)
- tensile_strength_mpa: 抗拉强度 (MPa)
- fracture_energy_kj_m2: 断裂能 (kJ/m²)

## 耐久性
- chloride_penetration_coefficient: 氯离子渗透系数
- carbonation_depth_mm: 碳化深度 (mm)
- freeze_thaw_resistance_cycles: 抗冻融循环次数

## 元数据
- test_method: 测试方法标准 (如 ASTM C109, JSCE SF-4)
- remarks: 备注信息

# 重要提示
1. 如果数值单位不是标准单位，请转换（如 psi → MPa 需乘以 0.006895）
2. 如果纤维掺量按质量给出，尝试根据上下文判断是否可以转换为体积掺量
3. 如果一个配比有多组养护条件下的数据，每种条件作为单独的一条记录
4. 同一配比在不同龄期的数据作为单独记录
5. 对于每个提取的数据，给出 confidence_score (0-1) 表示提取的可靠程度

# 输出格式
返回一个JSON对象，包含一个 "data_points" 数组：
{
  "data_points": [
    {
      "binder_type": "fly_ash",
      "fly_ash_ratio": 1.0,
      "water_binder_ratio": 0.30,
      "fiber_type": "PVA",
      "fiber_content_vol": 2.0,
      "compressive_strength_mpa": 52.3,
      "...": null,
      "confidence_score": 0.9,
      "remarks": "Table 2, Mix M3"
    }
  ]
}

只输出JSON，不要包含其他内容。
"""
