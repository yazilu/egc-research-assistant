"""
EGC 力学性能预测与配比优化服务

基于学术论文中提取的结构化实验数据，使用 LLM 进行：
1. 力学性能预测：给定配比 → 预测抗压强度、拉伸应变等
2. 配比优化：给定目标性能 → 建议最优配比
"""

import json
import logging
import os
from openai import OpenAI
from dotenv import load_dotenv
from database.egc_operations import get_similar_mixes
from service.core.retrieval import retrieve_content

load_dotenv()

logger = logging.getLogger(__name__)

PREDICTION_MODEL = os.getenv("EGC_PREDICTION_MODEL", "deepseek-v4-pro")
MAX_SIMILAR_MIXES = int(os.getenv("EGC_MAX_SIMILAR_MIXES", "10"))


def _format_mix_design(mix_design: dict) -> str:
    """格式化配比参数为可读文本"""
    lines = []
    field_labels = {
        'binder_type': '胶凝材料类型',
        'fly_ash_ratio': '粉煤灰比例',
        'slag_ratio': '矿渣比例',
        'metakaolin_ratio': '偏高岭土比例',
        'water_binder_ratio': '水胶比',
        'sand_binder_ratio': '砂胶比',
        'alkaline_activator_type': '碱激发剂类型',
        'naoh_molarity': 'NaOH浓度 (mol/L)',
        'na2sio3_naoh_ratio': 'Na2SiO3/NaOH比',
        'activator_modulus': '激发剂模数',
        'fiber_type': '纤维类型',
        'fiber_content_vol': '纤维体积掺量 (%)',
        'fiber_length': '纤维长度 (mm)',
        'fiber_diameter': '纤维直径 (μm)',
        'curing_age_days': '养护龄期 (天)',
        'curing_temperature': '养护温度 (℃)',
        'curing_method': '养护方式',
    }
    for key, label in field_labels.items():
        val = mix_design.get(key)
        if val is not None:
            lines.append(f"  {label}: {val}")
    return '\n'.join(lines)


def _format_experimental_data(similar_data: list) -> str:
    """格式化相似实验数据为表格文本"""
    if not similar_data:
        return "(无相似实验数据)"

    lines = ["序号 | 纤维类型 | 纤维掺量% | 水胶比 | 抗压强度MPa | 拉伸应变% | 养护龄期d"]
    lines.append("-" * 80)

    for i, row in enumerate(similar_data, 1):
        lines.append(
            f"  {i}  | {row.get('fiber_type','?')} | "
            f"{row.get('fiber_content_vol','?')} | "
            f"{row.get('water_binder_ratio','?')} | "
            f"{row.get('compressive_strength_mpa','?')} | "
            f"{row.get('ultimate_tensile_strain_pct','?')} | "
            f"{row.get('curing_age_days','?')}"
        )
    return '\n'.join(lines)


def _format_paper_chunks(chunks: list) -> str:
    """格式化论文检索片段"""
    if not chunks:
        return "(无相关论文片段)"

    lines = []
    for i, chunk in enumerate(chunks[:5], 1):
        content = chunk.get('content_with_weight', '')[:500]
        name = chunk.get('document_name', '?')
        lines.append(f"[{i}] 来源: {name}\n{content}\n")
    return '\n'.join(lines)


def predict_performance(mix_design: dict, user_id: str = "1") -> dict:
    """
    基于相似实验数据预测力学性能

    Args:
        mix_design: 用户输入的配比参数
        user_id: 用户 ID

    Returns:
        dict: 预测结果，包含各性能的预测值、置信区间和参考文献
    """
    from utils.egc_prompts import PerformancePredictionPrompt

    # 1. 查询相似配比的实验数据
    similar_data = get_similar_mixes(mix_design, top_k=MAX_SIMILAR_MIXES)
    logger.info(f"Found {len(similar_data)} similar experimental data points")

    # 2. 构建查询语句从 ES 检索相关论文
    query_parts = []
    if mix_design.get('fiber_type'):
        query_parts.append(f"{mix_design['fiber_type']} fiber")
    if mix_design.get('binder_type'):
        query_parts.append(f"{mix_design['binder_type']} based geopolymer")
    query_parts.append("EGC mechanical properties")
    es_query = " ".join(query_parts)

    try:
        es_results = retrieve_content(user_id, es_query)
    except Exception as e:
        logger.warning(f"ES retrieval failed: {e}")
        es_results = []

    # 3. 构造 Prompt
    mix_design_text = _format_mix_design(mix_design)
    experimental_text = _format_experimental_data(similar_data)
    paper_context = _format_paper_chunks(es_results)

    prompt = PerformancePredictionPrompt % (mix_design_text, experimental_text, paper_context)

    # 4. 调用 LLM 进行预测
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        completion = client.chat.completions.create(
            model=PREDICTION_MODEL,
            messages=[
                {'role': 'system', 'content': 'You are an expert in EGC mechanical properties prediction. Return valid JSON only.'},
                {'role': 'user', 'content': prompt}
            ],
            response_format={"type": "json_object"},
            stream=False,
        )

        result_text = completion.choices[0].message.content

        # 尝试提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_text = json_match.group(0)

        predictions = json.loads(result_text)
        predictions["status"] = "success"
        predictions["message"] = f"基于 {len(similar_data)} 组相似实验数据预测"
        predictions["similar_data_count"] = len(similar_data)
        predictions["references_count"] = len(es_results)

        return predictions

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse prediction result: {e}")
        return {
            "status": "error",
            "message": f"预测结果解析失败: {str(e)}",
            "similar_data_count": len(similar_data),
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return {
            "status": "error",
            "message": f"预测服务异常: {str(e)}",
        }


def optimize_mix(target_properties: dict, constraints: dict = None, user_id: str = "1") -> dict:
    """
    给定目标性能，建议最优配比

    Args:
        target_properties: 目标力学性能
        constraints: 可选约束条件
        user_id: 用户 ID

    Returns:
        dict: 优化建议
    """
    from utils.egc_prompts import MixOptimizationPrompt

    # 1. 根据目标性能查找已有的最优实验数据
    search_params = {}
    if constraints:
        search_params.update(constraints)

    similar_data = get_similar_mixes(search_params, top_k=MAX_SIMILAR_MIXES)

    # 2. 检索相关论文
    query_parts = ["EGC mix design optimization"]
    if target_properties.get('compressive_strength_min'):
        query_parts.append(f"high compressive strength")
    if target_properties.get('ultimate_tensile_strain_min'):
        query_parts.append(f"high tensile strain capacity")
    es_query = " ".join(query_parts)

    try:
        es_results = retrieve_content(user_id, es_query)
    except Exception as e:
        logger.warning(f"ES retrieval failed: {e}")
        es_results = []

    # 3. 构造 Prompt
    target_text = json.dumps(target_properties, ensure_ascii=False, indent=2)
    constraints_text = json.dumps(constraints, ensure_ascii=False, indent=2) if constraints else "(无约束条件)"
    experimental_text = _format_experimental_data(similar_data)
    paper_context = _format_paper_chunks(es_results)

    prompt = MixOptimizationPrompt % (target_text, constraints_text, experimental_text, paper_context)

    # 4. 调用 LLM
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        completion = client.chat.completions.create(
            model=PREDICTION_MODEL,
            messages=[
                {'role': 'system', 'content': 'You are an expert in EGC mix design optimization. Return valid JSON only.'},
                {'role': 'user', 'content': prompt}
            ],
            response_format={"type": "json_object"},
            stream=False,
        )

        result_text = completion.choices[0].message.content

        import re
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            result_text = json_match.group(0)

        optimization = json.loads(result_text)
        optimization["status"] = "success"
        optimization["message"] = f"基于 {len(similar_data)} 组实验数据的优化建议"

        return optimization

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse optimization result: {e}")
        return {"status": "error", "message": f"优化结果解析失败: {str(e)}"}
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        return {"status": "error", "message": f"优化服务异常: {str(e)}"}


def predict_from_query(query: str) -> list:
    """
    从自然语言查询中提供预测，作为 Agent 工具的一个 action。

    Args:
        query: 用户自然语言查询

    Returns:
        list: 包含预测信息的消息列表
    """
    return [{"message": f"预测查询已接收: {query}。请使用 /predict/ API 输入具体配比参数进行精确预测。"}]
