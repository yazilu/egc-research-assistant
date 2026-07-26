"""
EGC 论文元数据和实验数据智能提取服务

使用 LLM 从论文文本中自动提取：
1. 论文元数据（标题、作者、期刊、年份、DOI、摘要）
2. 结构化实验数据（材料配比、纤维信息、力学性能）
"""

import json
import logging
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# 提取用的模型
EXTRACTION_MODEL = os.getenv("EGC_EXTRACTION_MODEL", "deepseek-v4-flash")


def _call_llm(prompt: str, model: str = None) -> str:
    """调用 LLM 进行结构化提取"""
    client = OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    completion = client.chat.completions.create(
        model=model or EXTRACTION_MODEL,
        messages=[
            {'role': 'system', 'content': 'You are a precise data extraction assistant. Extract only factual information from the text.'},
            {'role': 'user', 'content': prompt}
        ],
        response_format={"type": "json_object"}
    )
    return completion.choices[0].message.content


def _merge_chunks(chunks: list, max_tokens: int = 8000) -> str:
    """将 chunks 列表合并为单个文本，限制最大长度"""
    text = ""
    for chunk in chunks:
        chunk_text = chunk.get("content_with_weight", "")
        if len(text) + len(chunk_text) > max_tokens:
            text += chunk_text[:max_tokens - len(text)]
            break
        text += chunk_text + "\n\n"
    return text


def extract_paper_metadata(chunks: list) -> dict:
    """
    从论文文本 chunks 中提取论文元数据

    Args:
        chunks: 从 ES 检索或解析得到的 chunks 列表，
                每个 chunk 包含 content_with_weight 字段

    Returns:
        dict: 论文元数据，字段：title, authors, journal,
              publication_year, doi, abstract
    """
    from utils.egc_prompts import PaperMetadataExtractionPrompt

    text = _merge_chunks(chunks, max_tokens=4000)
    if not text.strip():
        logger.warning("Empty text provided for metadata extraction")
        return {}

    prompt = PaperMetadataExtractionPrompt % text

    try:
        result = _call_llm(prompt)
        metadata = json.loads(result)
        if "title" in metadata and "paper_title" not in metadata:
            metadata["paper_title"] = metadata.pop("title")
        logger.info("Extracted paper metadata fields: %s", sorted(metadata.keys()))
        return metadata
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse metadata extraction result: {e}")
        return {}
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {}


def extract_experimental_data(chunks: list) -> list:
    """
    从论文文本 chunks 中提取结构化实验数据

    Args:
        chunks: 从 ES 检索或解析得到的 chunks 列表

    Returns:
        list[dict]: 实验数据点列表，每个元素对应 egc_experimental_data 表的一行
    """
    from utils.egc_prompts import ExperimentalDataExtractionPrompt

    text = _merge_chunks(chunks, max_tokens=8000)
    if not text.strip():
        logger.warning("Empty text provided for experimental data extraction")
        return []

    prompt = ExperimentalDataExtractionPrompt % text

    try:
        result = _call_llm(prompt)
        parsed = json.loads(result)
        data_points = parsed.get("data_points", [])
        logger.info(f"Extracted {len(data_points)} experimental data points")
        return data_points
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse experimental data extraction result: {e}")
        return []
    except Exception as e:
        logger.error(f"Experimental data extraction failed: {e}")
        return []


def normalize_experimental_data(raw_data: list) -> list:
    """
    对提取的实验数据进行标准化处理：
    - 过滤掉置信度过低的记录
    - 确保数值字段类型正确
    - 标记提取来源

    Args:
        raw_data: extract_experimental_data 返回的原始数据

    Returns:
        list[dict]: 标准化后的数据
    """
    normalized = []
    numeric_fields = [
        'fly_ash_ratio', 'slag_ratio', 'metakaolin_ratio',
        'water_binder_ratio', 'sand_binder_ratio',
        'naoh_molarity', 'na2sio3_naoh_ratio', 'activator_modulus',
        'fiber_content_vol', 'fiber_length', 'fiber_diameter',
        'fiber_tensile_strength', 'fiber_elastic_modulus',
        'curing_age_days', 'curing_temperature',
        'compressive_strength_mpa', 'ultimate_tensile_strain_pct',
        'flexural_strength_mpa', 'elastic_modulus_gpa',
        'tensile_strength_mpa', 'fracture_energy_kj_m2',
        'chloride_penetration_coefficient', 'carbonation_depth_mm',
        'freeze_thaw_resistance_cycles',
        'confidence_score'
    ]

    for item in raw_data:
        # 跳过低置信度记录
        if item.get('confidence_score', 0) is not None and item['confidence_score'] < 0.4:
            continue

        # 确保数值字段类型正确
        for field in numeric_fields:
            if field in item and item[field] is not None:
                try:
                    item[field] = float(item[field])
                except (ValueError, TypeError):
                    item[field] = None

        item['extracted_by'] = 'llm'
        normalized.append(item)

    logger.info(f"Normalized {len(normalized)} data points (filtered from {len(raw_data)} raw)")
    return normalized
